"""Tests for S3 ingestion and loader utilities."""
from __future__ import annotations

from pathlib import Path

from extractors.base_extractor import BaseExtractor
from ingestors.s3_ingestor import IngestedFile, S3Ingestor
from loaders.s3_loader import S3Loader
from loaders.postgres_loader import PostgresLoader
from models.database_models import Bidder


class FakePaginator:
    def __init__(self, pages):
        self.pages = pages

    def paginate(self, **_kwargs):
        return self.pages


class FakeS3Client:
    def __init__(self, pages=None):
        self.pages = pages or []
        self.downloaded = []
        self.uploads = []
        self.copies = []
        self.deletes = []

    def get_paginator(self, _name):
        return FakePaginator(self.pages)

    def download_file(self, bucket, key, filename):
        self.downloaded.append((bucket, key, filename))
        Path(filename).write_bytes(b"%PDF-1.4")

    def upload_file(self, filename, bucket, key):
        self.uploads.append((filename, bucket, key))

    def copy_object(self, **kwargs):
        self.copies.append(kwargs)

    def delete_object(self, **kwargs):
        self.deletes.append(kwargs)


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter_by(self, **_kwargs):
        return self

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, rows):
        self.rows = rows
        self.added = []

    def query(self, _model):
        return FakeQuery(self.rows)

    def add(self, item):
        self.added.append(item)

    def commit(self):
        return None

    def rollback(self):
        return None


def test_s3_ingestor_lists_and_downloads(tmp_path):
    pages = [
        {"Contents": [
            {"Key": "raw/one.pdf"},
            {"Key": "raw/two.txt"},
            {"Key": "raw/three.PDF"},
        ]}
    ]
    client = FakeS3Client(pages=pages)
    ingestor = S3Ingestor(
        bucket="bucket",
        raw_prefix="raw/",
        local_dir=tmp_path,
        max_items=2,
        s3_client=client,
    )

    files = ingestor.download_all()

    assert [f.key for f in files] == ["raw/one.pdf", "raw/three.PDF"]
    assert len(client.downloaded) == 2
    assert files[0].local_path.exists()


def test_s3_ingestor_build_key_map(tmp_path):
    files = [
        IngestedFile(key="raw/one.pdf", local_path=tmp_path / "one.pdf"),
        IngestedFile(key="raw/two.pdf", local_path=tmp_path / "two.pdf"),
    ]
    key_map = S3Ingestor.build_key_map(files)

    assert key_map[str(tmp_path / "one.pdf")] == "raw/one.pdf"
    assert key_map[str(tmp_path / "two.pdf")] == "raw/two.pdf"


def test_s3_loader_upload_and_move(tmp_path):
    client = FakeS3Client()
    loader = S3Loader(
        bucket="bucket",
        processed_prefix="processed/",
        error_prefix="error/",
        s3_client=client,
    )

    results = [{"file_path": "a.pdf", "status": "success"}]
    key = loader.upload_results(results, output_format="jsonl")

    assert key.startswith("processed/results/")
    assert len(client.uploads) == 1

    moved_key = loader.move_source("raw/a.pdf", success=False)
    assert moved_key == "error/a.pdf"
    assert len(client.copies) == 1
    assert len(client.deletes) == 1


def test_postgres_loader_dedup_bidders():
    loader = PostgresLoader.__new__(PostgresLoader)
    existing = [Bidder(bidder_name="ACME", total_bid_amount=100.0)]
    loader.session = FakeSession(existing)

    bidders = [
        {"bidder_name": "ACME", "total_bid_amount": 100.0},
        {"bidder_name": "ACME", "total_bid_amount": 100.0},
        {"bidder_name": "ACME", "total_bid_amount": 200.0},
    ]

    count = PostgresLoader.load_bidders(loader, contract_id=1, bidders=bidders)

    assert count == 1
    assert len(loader.session.added) == 1
    assert loader.session.added[0].total_bid_amount == 200.0


def test_postgres_loader_partial_loads_data():
    loader = PostgresLoader.__new__(PostgresLoader)
    loader.log_extraction = lambda _result: None

    captured = {}

    class DummyContract:
        id = 7

    def fake_load_contract(data):
        captured["contract_number"] = data.get("contract_number")
        return DummyContract()

    loader.load_contract = fake_load_contract
    loader.load_bidders = lambda _contract_id, _bidders: 1
    loader.load_bid_items = lambda _contract_id, _items: 0

    result = {
        "status": "partial",
        "data": {"contract_number": " da123 "},
        "file_path": "file.pdf",
    }

    assert PostgresLoader.load_extraction_result(loader, result) is True
    assert captured["contract_number"] == "DA123"
