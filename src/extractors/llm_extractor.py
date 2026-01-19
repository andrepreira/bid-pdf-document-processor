"""LLM-based extractor with provider-agnostic implementation."""
import json
import os
from typing import Dict, Optional, Any
from pathlib import Path

import structlog
from litellm import completion

from .base_extractor import BaseExtractor

logger = structlog.get_logger()


class LLMExtractor(BaseExtractor):
    """Generic LLM extractor supporting multiple providers.
    
    Supports:
    - Google Gemini (gemini/gemini-pro, gemini/gemini-1.5-pro)
    - OpenAI (gpt-4, gpt-4-turbo, gpt-3.5-turbo)
    - Anthropic Claude (claude-3-opus, claude-3-sonnet, claude-3-haiku)
    - Ollama (local models like llama2, mistral)
    - Any provider supported by LiteLLM
    """
    
    def __init__(
        self,
        pdf_path: str | Path,
        model: str = "gemini/gemini-1.5-flash-latest",
        api_key: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4000
    ):
        """Initialize LLM extractor.
        
        Args:
            pdf_path: Path to PDF file
            model: Model identifier (e.g., 'gemini/gemini-1.5-flash-latest', 'gpt-4', 'claude-3-sonnet')
            api_key: API key for the provider (or None to use env vars)
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens in response
        """
        super().__init__(pdf_path)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Set API key if provided
        if api_key:
            self._set_api_key(api_key)
        
        # Validate model is configured
        self._validate_configuration()
    
    def _set_api_key(self, api_key: str):
        """Set API key for the provider based on model."""
        if "gemini" in self.model.lower():
            os.environ["GEMINI_API_KEY"] = api_key
        elif "gpt" in self.model.lower():
            os.environ["OPENAI_API_KEY"] = api_key
        elif "claude" in self.model.lower():
            os.environ["ANTHROPIC_API_KEY"] = api_key
    
    def _validate_configuration(self):
        """Validate that required API keys are set."""
        if "gemini" in self.model.lower() and not os.getenv("GEMINI_API_KEY"):
            raise ValueError("GEMINI_API_KEY not found in environment")
        elif "gpt" in self.model.lower() and not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found in environment")
        elif "claude" in self.model.lower() and not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
    
    def _create_extraction_prompt(self, text: str, document_type: str) -> str:
        """Create extraction prompt based on document type.
        
        Args:
            text: PDF text content
            document_type: Type of document to extract
            
        Returns:
            Formatted prompt for LLM
        """
        base_prompt = f"""You are a data extraction expert. Extract structured information from this {document_type} document.

Document Content:
{text[:8000]}  # Limit text to avoid token limits

IMPORTANT: Return ONLY valid JSON with the extracted fields. No explanations or markdown.

"""
        
        if document_type == "invitation_to_bid":
            schema = {
                "contract_number": "string (e.g., DA00565)",
                "letting_date": "string (YYYY-MM-DD)",
                "bid_opening_date": "string (YYYY-MM-DD)",
                "project_description": "string",
                "mbe_goal_percent": "number (e.g., 10 for 10%)",
                "wbe_goal_percent": "number",
                "location": "string",
                "county": "string"
            }
        elif document_type == "bid_tabs":
            schema = {
                "contract_number": "string",
                "letting_date": "string (YYYY-MM-DD)",
                "bidders": [
                    {
                        "rank": "integer",
                        "company_name": "string",
                        "total_bid": "number (dollars)"
                    }
                ]
            }
        elif document_type == "award_letter":
            schema = {
                "contract_number": "string",
                "award_date": "string (YYYY-MM-DD)",
                "winner_name": "string",
                "award_amount": "number (dollars)",
                "project_description": "string"
            }
        elif document_type == "item_c_report":
            schema = {
                "letting_date": "string (YYYY-MM-DD)",
                "engineer_estimate": "number (dollars)",
                "low_bid": "number (dollars)",
                "bidders": [
                    {
                        "company_name": "string",
                        "total_bid": "number"
                    }
                ]
            }
        else:
            schema = {"error": "Unknown document type"}
        
        return base_prompt + f"\nExpected JSON Schema:\n{json.dumps(schema, indent=2)}\n\nExtracted Data (JSON only):"
    
    def extract_with_llm(self, document_type: str = "unknown") -> Dict:
        """Extract data using LLM.
        
        Args:
            document_type: Type of document being processed
            
        Returns:
            Dictionary with extracted data
        """
        try:
            # Extract text from PDF
            text = self.extract_text()
            
            # Create prompt
            prompt = self._create_extraction_prompt(text, document_type)
            
            # Call LLM via LiteLLM (handles multiple providers)
            logger.info(
                "Calling LLM for extraction",
                model=self.model,
                file=self.pdf_name
            )
            
            # Prepare API key for Google Gemini
            # LiteLLM expects format: gemini/<model-name>
            # E.g. gemini/gemini-1.5-flash-latest
            api_key = None
            model_name = self.model
            
            if "gemini" in model_name.lower():
                api_key = os.getenv("GEMINI_API_KEY")
                # Ensure proper format: gemini/<model-name>
                if "/" not in model_name:
                    # User passed just "gemini-1.5-flash-latest", add prefix
                    model_name = f"gemini/{model_name}"
                elif not model_name.startswith("gemini/"):
                    # User passed something like "google/gemini-1.5-flash-latest"
                    # Extract model part and fix prefix
                    model_part = model_name.split("/")[-1]
                    model_name = f"gemini/{model_part}"
            
            response = completion(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                api_key=api_key
            )
            
            # Extract response content
            content = response.choices[0].message.content
            
            # Parse JSON response
            # Remove markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            data = json.loads(content.strip())
            
            logger.info(
                "LLM extraction successful",
                model=self.model,
                fields_extracted=len(data)
            )
            
            return data
            
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse LLM response as JSON: {str(e)}"
            logger.error("JSON parsing error", error=error_msg, response_preview=content[:200] if 'content' in locals() else 'N/A')
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"LLM extraction failed: {str(e)}"
            logger.error("LLM extraction error", error=error_msg)
            raise RuntimeError(error_msg)
    
    def extract(self) -> Dict:
        """Main extraction method (implements BaseExtractor interface).
        
        Returns:
            Dictionary with extracted data
        """
        # Try to infer document type from filename
        filename_lower = self.pdf_path.name.lower()
        
        if "invitation" in filename_lower:
            doc_type = "invitation_to_bid"
        elif "bid tab" in filename_lower or "bidtab" in filename_lower:
            doc_type = "bid_tabs"
        elif "award" in filename_lower:
            doc_type = "award_letter"
        elif "item c" in filename_lower or "itemc" in filename_lower:
            doc_type = "item_c_report"
        else:
            doc_type = "unknown"
        
        return self.extract_with_llm(doc_type)


class HybridExtractor:
    """Hybrid extractor that tries traditional methods first, falls back to LLM."""
    
    def __init__(
        self,
        traditional_extractor: BaseExtractor,
        llm_model: str = "gemini/gemini-1.5-flash",
        llm_api_key: Optional[str] = None,
        confidence_threshold: float = 0.5
    ):
        """Initialize hybrid extractor.
        
        Args:
            traditional_extractor: Instance of a traditional extractor
            llm_model: LLM model to use for fallback
            llm_api_key: API key for LLM provider
            confidence_threshold: Minimum confidence to accept traditional result
        """
        self.traditional = traditional_extractor
        self.llm_model = llm_model
        self.llm_api_key = llm_api_key
        self.confidence_threshold = confidence_threshold
    
    def extract(self) -> Dict:
        """Extract using traditional method first, LLM as fallback.
        
        Returns:
            Dictionary with extracted data and metadata
        """
        # Try traditional extraction
        trad_result = self.traditional.run_extraction()
        
        if trad_result["status"] == "success":
            confidence = self.traditional.calculate_confidence_score(
                trad_result["data"]
            )
            
            # If confidence is high enough, use traditional result
            if confidence >= self.confidence_threshold:
                logger.info(
                    "Using traditional extraction",
                    confidence=f"{confidence:.2f}",
                    file=self.traditional.pdf_name
                )
                trad_result["metadata"]["confidence"] = confidence
                trad_result["metadata"]["method_used"] = "traditional"
                return trad_result
        
        # Fall back to LLM
        logger.info(
            "Traditional extraction insufficient, using LLM fallback",
            file=self.traditional.pdf_name
        )
        
        try:
            llm_extractor = LLMExtractor(
                self.traditional.pdf_path,
                model=self.llm_model,
                api_key=self.llm_api_key
            )
            
            llm_result = llm_extractor.run_extraction()
            llm_result["metadata"]["method_used"] = "llm_fallback"
            llm_result["metadata"]["traditional_confidence"] = confidence if 'confidence' in locals() else 0.0
            
            return llm_result
            
        except Exception as e:
            logger.error("LLM fallback failed", error=str(e))
            # Return original traditional result even if low confidence
            trad_result["metadata"]["llm_fallback_failed"] = True
            return trad_result
