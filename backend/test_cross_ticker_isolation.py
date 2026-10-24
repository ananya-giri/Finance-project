import os
import sys
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.models.unstructured_doc import UnstructuredDocument
from backend.app.models.document_chunk import DocumentChunk
from backend.app.models.company import Company
from backend.app.models.structured_metrics import StructuredMetric
from backend.app.models.market_intelligence import EconomicIndicator
from backend.app.services.document_ingestion import DocumentIngestionService
from backend.app.services.rag_service import RAGService
from backend.repair_contaminated_transcripts import (
    execute_repair,
    AFFECTED_DOC_IDS,
    EXPECTED_DOC_COUNT,
    EXPECTED_CHUNK_COUNT
)

DATA_DIR = PROJECT_ROOT / "data"
PROD_DB_PATH = DATA_DIR / "fintech.db"
PROD_UPLOAD_DIR = DATA_DIR / "uploads"

def run_all_tests():
    print("==================================================================")
    print(" AAPL/APEX CONTAMINATION REPAIR & CROSS-TICKER ISOLATION TEST SUITE")
    print(" (STRICTLY ISOLATED TEMPORARY ENVIRONMENT - ZERO LIVE DATA MUTATION)")
    print("==================================================================")

    # -----------------------------------------------------------------
    # TEST 1: Read-Only Verification of Production Preflight State
    # -----------------------------------------------------------------
    print("\n--- TEST 1: Read-Only Preflight Verification of Production DB ---")
    assert PROD_DB_PATH.exists(), f"Production database missing at {PROD_DB_PATH}"
    ro_conn = sqlite3.connect(f"file:{PROD_DB_PATH}?mode=ro", uri=True)
    try:
        cur = ro_conn.cursor()
        cur.execute("PRAGMA integrity_check;")
        assert cur.fetchall() == [("ok",)], "Production DB integrity check failed"

        # Check affected documents
        cur.execute(f"""
            SELECT id, ticker, doc_type, fiscal_period, title, file_path
            FROM unstructured_documents
            WHERE id IN ({','.join(map(str, AFFECTED_DOC_IDS))})
            ORDER BY id;
        """)
        affected_docs = cur.fetchall()
        assert len(affected_docs) == EXPECTED_DOC_COUNT, f"Expected {EXPECTED_DOC_COUNT} affected docs, found {len(affected_docs)}"
        for doc in affected_docs:
            d_id, ticker, doc_type, period, title, fpath = doc
            assert ticker == "AAPL", f"Doc #{d_id} expected ticker AAPL, got {ticker}"
            assert doc_type == "EARNINGS_CALL_TRANSCRIPT", f"Doc #{d_id} expected EARNINGS_CALL_TRANSCRIPT"
            p = Path(fpath)
            if p.exists():
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                assert "Apex Financial Systems Inc. (APEX)" in content, f"Doc #{d_id} upload missing APEX content"

        # Check affected chunks
        cur.execute(f"SELECT COUNT(*) FROM document_chunks WHERE document_id IN ({','.join(map(str, AFFECTED_DOC_IDS))});")
        affected_chunks_count = cur.fetchone()[0]
        assert affected_chunks_count == EXPECTED_CHUNK_COUNT, f"Expected {EXPECTED_CHUNK_COUNT} chunks, got {affected_chunks_count}"

        # Check that unaffected documents do not cross-reference affected upload files
        affected_filenames = [Path(doc[5]).name for doc in affected_docs]
        placeholders = ",".join(f"'{name}'" for name in affected_filenames)
        cur.execute(f"""
            SELECT COUNT(*) FROM unstructured_documents
            WHERE id NOT IN ({','.join(map(str, AFFECTED_DOC_IDS))})
              AND file_name IN ({placeholders});
        """)
        cross_refs = cur.fetchone()[0]
        assert cross_refs == 0, f"Unaffected documents cross-reference affected files: {cross_refs}"

        print(f"[PASS] Preflight Verified: Found exactly {len(affected_docs)} docs and {affected_chunks_count} chunks with APEX content under AAPL metadata.")
        print("       Zero cross-references from unaffected documents.")
    finally:
        ro_conn.close()

    # -----------------------------------------------------------------
    # Setup Temporary Sandbox Environment for Tests 2 - 7
    # -----------------------------------------------------------------
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        temp_db_path = temp_dir_path / "fintech_isolated.db"
        temp_upload_dir = temp_dir_path / "uploads"
        temp_upload_dir.mkdir(parents=True, exist_ok=True)

        # Copy production database and upload files to isolated sandbox
        shutil.copy2(PROD_DB_PATH, temp_db_path)
        if PROD_UPLOAD_DIR.exists():
            for f in PROD_UPLOAD_DIR.iterdir():
                if f.is_file():
                    shutil.copy2(f, temp_upload_dir / f.name)

        # -----------------------------------------------------------------
        # TEST 2: Repair Script Dry-Run Simulation (No Mutations)
        # -----------------------------------------------------------------
        print("\n--- TEST 2: Repair Script Dry-Run on Isolated Copy ---")
        execute_repair(dry_run=True, db_path=temp_db_path, upload_dir=temp_upload_dir)

        # Verify that dry-run modified zero records
        check_conn = sqlite3.connect(str(temp_db_path))
        try:
            c = check_conn.cursor()
            c.execute(f"SELECT COUNT(*) FROM unstructured_documents WHERE id IN ({','.join(map(str, AFFECTED_DOC_IDS))});")
            assert c.fetchone()[0] == EXPECTED_DOC_COUNT, "Dry-run modified unstructured_documents!"
            c.execute(f"SELECT COUNT(*) FROM document_chunks WHERE document_id IN ({','.join(map(str, AFFECTED_DOC_IDS))});")
            assert c.fetchone()[0] == EXPECTED_CHUNK_COUNT, "Dry-run modified document_chunks!"
        finally:
            check_conn.close()
        print("[PASS] Dry-run simulated successfully with zero modifications.")

        # -----------------------------------------------------------------
        # TEST 3: Repair Script Live Execution on Isolated Copy
        # -----------------------------------------------------------------
        print("\n--- TEST 3: Repair Script Live Execution on Isolated Copy ---")
        execute_repair(dry_run=False, db_path=temp_db_path, upload_dir=temp_upload_dir)

        # Verify post-repair database state
        verif_conn = sqlite3.connect(str(temp_db_path))
        try:
            c = verif_conn.cursor()
            c.execute("PRAGMA integrity_check;")
            assert c.fetchall() == [("ok",)], "Integrity check failed post-repair"

            c.execute(f"SELECT COUNT(*) FROM unstructured_documents WHERE id IN ({','.join(map(str, AFFECTED_DOC_IDS))});")
            assert c.fetchone()[0] == 0, "Contaminated documents still remain after repair"

            c.execute(f"SELECT COUNT(*) FROM document_chunks WHERE document_id IN ({','.join(map(str, AFFECTED_DOC_IDS))});")
            assert c.fetchone()[0] == 0, "Contaminated chunks still remain after repair"

            # Check for backup database and JSON export files in sandbox
            bak_dbs = list(temp_dir_path.glob("*.bak_pre_contamination_repair_*"))
            assert len(bak_dbs) >= 1, "Cold database backup was not created"
            bak_jsons = list(temp_dir_path.glob("backup_contaminated_records_*.json"))
            assert len(bak_jsons) >= 1, "JSON export backup was not created"

            with open(bak_jsons[0], "r", encoding="utf-8") as jf:
                payload = json.load(jf)
                assert payload["total_documents"] == EXPECTED_DOC_COUNT
                assert payload["total_chunks"] == EXPECTED_CHUNK_COUNT
                assert len(payload["unstructured_documents"]) == EXPECTED_DOC_COUNT
                assert len(payload["document_chunks"]) == EXPECTED_CHUNK_COUNT

            # Check for archive directory and manifest
            archive_dirs = list(temp_upload_dir.glob("archive_contaminated_aapl_transcripts_*"))
            assert len(archive_dirs) >= 1, "Archive directory was not created"
            manifest_path = archive_dirs[0] / "archive_manifest.json"
            assert manifest_path.exists(), "Archive manifest missing"

            with open(manifest_path, "r", encoding="utf-8") as mf:
                manifest_data = json.load(mf)
                assert len(manifest_data["files"]) == EXPECTED_DOC_COUNT

            print(f"[PASS] Safe Repair Live Execution Verified: {EXPECTED_DOC_COUNT} documents and {EXPECTED_CHUNK_COUNT} chunks atomically removed.")
            print(f"       Cold backup verified: {bak_dbs[0].name}")
            print(f"       JSON backup verified: {bak_jsons[0].name}")
            print(f"       Archive manifest verified: {archive_dirs[0].name}")
        finally:
            verif_conn.close()

        # -----------------------------------------------------------------
        # Set up SQLAlchemy Session on Repaired Isolated Database
        # -----------------------------------------------------------------
        test_engine = create_engine(f"sqlite:///{temp_db_path}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=test_engine)
        TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
        test_db = TestSession()

        import backend.app.config
        import backend.app.services.document_ingestion
        import backend.app.services.rag_service
        orig_upload_dir = backend.app.config.UPLOAD_DIR
        backend.app.config.UPLOAD_DIR = temp_upload_dir
        backend.app.services.document_ingestion.UPLOAD_DIR = temp_upload_dir
        backend.app.services.rag_service.UPLOAD_DIR = temp_upload_dir

        try:
            # -----------------------------------------------------------------
            # TEST 4: Clean Ingestion of Sample Transcript with APEX Metadata
            # -----------------------------------------------------------------
            print("\n--- TEST 4: Clean APEX Transcript Ingestion & Idempotency ---")
            sample_file = PROJECT_ROOT / "sample_data" / "sample_earnings_transcript.txt"
            assert sample_file.exists(), "Sample earnings transcript file missing"
            with open(sample_file, "rb") as f:
                sample_bytes = f.read()

            ingest_res = DocumentIngestionService.ingest_document(
                db=test_db,
                ticker="APEX",
                doc_type="EARNINGS_CALL_TRANSCRIPT",
                title="Apex Financial Systems Q3 FY25 Earnings Call",
                file_bytes=sample_bytes,
                original_filename="sample_earnings_transcript.txt",
                fiscal_period="2025-Q3",
                period_type="QUARTERLY",
                custom_metadata={"industry": "Fintech", "confidence_score": 0.95}
            )
            doc_id = ingest_res["document_id"]
            chunks_count = ingest_res["chunks_indexed"]
            assert chunks_count > 0, "No chunks were indexed"
            print(f"  Ingested Doc #{doc_id}: {ingest_res['title']} ({chunks_count} chunks)")

            # Verify idempotency
            reindex_res = RAGService.index_document(test_db, doc_id, force=False)
            assert reindex_res["status"] == "UNCHANGED"
            print("  Idempotent re-indexing verified: status=UNCHANGED")
            print("[PASS] Clean APEX transcript ingestion and idempotent indexing verified.")

            # -----------------------------------------------------------------
            # TEST 5: Cross-Ticker Evidence Isolation Post-Repair
            # -----------------------------------------------------------------
            print("\n--- TEST 5: Cross-Ticker Evidence Isolation Post-Repair ---")
            # 5A: Query for APEX
            apex_search = RAGService.search_evidence(test_db, query="operating margin and revenue", ticker="APEX", top_k=5)
            assert apex_search["results_count"] > 0
            for ev in apex_search["evidence"]:
                assert ev["ticker"] == "APEX", f"Expected APEX, got {ev['ticker']}"
                assert "apple" not in ev["text"].lower() and "iphone" not in ev["text"].lower(), "APEX chunk contaminated with Apple"
            print(f"  APEX search returned {apex_search['results_count']} clean APEX results.")

            # 5B: Query for AAPL earnings conference call
            aapl_search = RAGService.search_evidence(test_db, query="CEO commentary on operating margin in earnings call", ticker="AAPL", top_k=5)
            for ev in aapl_search["evidence"]:
                assert "apex" not in ev["text"].lower(), f"AAPL search returned contaminated APEX text: {ev['text']}"
                assert "apex" not in ev["title"].lower(), f"AAPL search returned APEX title: {ev['title']}"
            print(f"  AAPL search isolated: zero contaminated APEX evidence returned.")

            # 5C: Grounded recommendation for APEX
            apex_rec = RAGService.generate_grounded_recommendation(
                test_db,
                query="Evaluate operating margin and revenue performance for APEX",
                ticker="APEX"
            )
            assert apex_rec["status"] == "GROUNDED"
            assert apex_rec["grounded"] is True
            assert len(apex_rec["citations"]) > 0
            for cite in apex_rec["citations"]:
                assert cite["ticker"] == "APEX"
                assert "apple" not in cite["excerpt"].lower()
            print("  APEX recommendation correctly grounded with clean citations.")

            # 5D: Grounded recommendation for AAPL (no earnings call in KB for AAPL)
            aapl_rec = RAGService.generate_grounded_recommendation(
                test_db,
                query="What was the CEO commentary on operating margin in the earnings conference call?",
                ticker="AAPL"
            )
            assert aapl_rec["status"] == "INSUFFICIENT_EVIDENCE", f"Expected INSUFFICIENT_EVIDENCE, got {aapl_rec['status']}"
            assert aapl_rec["grounded"] is False
            assert len(aapl_rec["citations"]) == 0
            assert "INSUFFICIENT EVIDENCE" in aapl_rec["recommendation"]
            print("  AAPL earnings call query triggered FR-014 INSUFFICIENT_EVIDENCE guardrail (Hallucination prevented).")
            print("[PASS] Cross-ticker isolation strictly enforced between AAPL and APEX.")

            # -----------------------------------------------------------------
            # TEST 6: FR-014 Out-of-Domain Insufficient Evidence Guardrail
            # -----------------------------------------------------------------
            print("\n--- TEST 6: FR-014 Out-of-Domain Guardrail ---")
            unsupported_rec = RAGService.generate_grounded_recommendation(
                test_db,
                query="Provide the 2038 deep space lunar rover battery telemetry specifications",
                ticker="APEX"
            )
            assert unsupported_rec["status"] == "INSUFFICIENT_EVIDENCE"
            assert unsupported_rec["grounded"] is False
            assert len(unsupported_rec["citations"]) == 0
            assert "INSUFFICIENT EVIDENCE" in unsupported_rec["recommendation"]
            print("  Out-of-domain query correctly triggered FR-014 INSUFFICIENT_EVIDENCE guardrail.")
            print("[PASS] FR-014 anti-hallucination guardrail verified.")

            # -----------------------------------------------------------------
            # TEST 7: Zero Regression on FR-001 through FR-009 Records
            # -----------------------------------------------------------------
            print("\n--- TEST 7: Regression Check for FR-001 through FR-009 ---")
            companies_count = test_db.query(Company).count()
            metrics_count = test_db.query(StructuredMetric).count()
            indicators_count = test_db.query(EconomicIndicator).count()

            print(f"  Tracked Companies: {companies_count}")
            print(f"  Structured Metric Records: {metrics_count}")
            print(f"  Economic Indicators: {indicators_count}")

            assert companies_count >= 5, f"Expected at least 5 companies, got {companies_count}"
            assert metrics_count >= 30, f"Expected at least 30 structured metrics, got {metrics_count}"
            assert indicators_count >= 20, f"Expected at least 20 economic indicators, got {indicators_count}"
            print("[PASS] FR-001 to FR-009 structured metrics and indicators completely intact.")

        finally:
            test_db.close()
            test_engine.dispose()
            backend.app.config.UPLOAD_DIR = orig_upload_dir
            backend.app.services.document_ingestion.UPLOAD_DIR = orig_upload_dir
            backend.app.services.rag_service.UPLOAD_DIR = orig_upload_dir

    # -----------------------------------------------------------------
    # Helper for Failure-Injection Sandboxes
    # -----------------------------------------------------------------
    import hashlib
    from backend.repair_contaminated_transcripts import archive_upload_files

    import gc

    def setup_sandbox(temp_dir_path: Path):
        t_db = temp_dir_path / "fintech_isolated.db"
        t_up = temp_dir_path / "uploads"
        t_up.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROD_DB_PATH, t_db)
        if PROD_UPLOAD_DIR.exists():
            for f in PROD_UPLOAD_DIR.iterdir():
                if f.is_file():
                    shutil.copy2(f, t_up / f.name)
        return t_db, t_up

    def get_counts(db_path: Path):
        c = sqlite3.connect(str(db_path))
        try:
            cur = c.cursor()
            cur.execute(f"SELECT COUNT(*) FROM unstructured_documents WHERE id IN ({','.join(map(str, AFFECTED_DOC_IDS))});")
            d_count = cur.fetchone()[0]
            cur.execute(f"SELECT COUNT(*) FROM document_chunks WHERE document_id IN ({','.join(map(str, AFFECTED_DOC_IDS))});")
            c_count = cur.fetchone()[0]
            return d_count, c_count
        finally:
            c.close()

    # -----------------------------------------------------------------
    # TEST 8: Failure Injection - Archive Failure with Auto-Rollback
    # -----------------------------------------------------------------
    print("\n--- TEST 8: Failure Injection - Archive Failure with Auto-Rollback ---")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        t_db, t_up = setup_sandbox(Path(temp_dir))
        files_before = set(f.name for f in t_up.iterdir() if f.is_file())

        move_count = 0
        def fail_on_second_move(event, **kwargs):
            nonlocal move_count
            if event == "archive_file_move":
                move_count += 1
                if move_count >= 2:
                    raise PermissionError("Simulated OS permission denied during file move")

        failed = False
        try:
            execute_repair(dry_run=False, db_path=t_db, upload_dir=t_up, _failure_hook=fail_on_second_move)
        except PermissionError:
            failed = True
        assert failed, "Expected PermissionError during file move"

        files_after = set(f.name for f in t_up.iterdir() if f.is_file())
        assert files_after == files_before, f"Uploads directory inconsistent after archive failure! Missing: {files_before - files_after}"

        # DB must remain completely unchanged
        docs, chunks = get_counts(t_db)
        assert docs == EXPECTED_DOC_COUNT
        assert chunks == EXPECTED_CHUNK_COUNT
        print("[PASS] Archive failure handled: moved files restored, database untouched, 100% consistent.")
        gc.collect()

    # -----------------------------------------------------------------
    # TEST 9: Failure Injection - Chunk Row Count Mismatch with Auto-Rollback
    # -----------------------------------------------------------------
    print("\n--- TEST 9: Failure Injection - Chunk Row Count Mismatch with Auto-Rollback ---")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        t_db, t_up = setup_sandbox(Path(temp_dir))
        files_before = set(f.name for f in t_up.iterdir() if f.is_file())

        def fail_on_chunk_check(event, **kwargs):
            if event == "post_chunk_delete":
                raise RuntimeError("Simulated chunk row count mismatch: expected 27, got 26")

        failed = False
        try:
            execute_repair(dry_run=False, db_path=t_db, upload_dir=t_up, _failure_hook=fail_on_chunk_check)
        except RuntimeError as re:
            failed = True
            assert "Simulated chunk row count mismatch" in str(re)
        assert failed, "Expected RuntimeError on chunk count mismatch"

        # Assert moved files were rolled back and restored to upload dir
        files_after = set(f.name for f in t_up.iterdir() if f.is_file())
        assert files_after == files_before, "Files not restored after chunk count failure"

        # Assert SQL transaction was rolled back (documents and chunks still exist)
        docs, chunks = get_counts(t_db)
        assert docs == EXPECTED_DOC_COUNT
        assert chunks == EXPECTED_CHUNK_COUNT
        print("[PASS] Chunk row-count failure handled: SQL rolled back, archived files restored to uploads.")
        gc.collect()

    # -----------------------------------------------------------------
    # TEST 10: Failure Injection - Document Row Count Mismatch with Auto-Rollback
    # -----------------------------------------------------------------
    print("\n--- TEST 10: Failure Injection - Document Row Count Mismatch with Auto-Rollback ---")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        t_db, t_up = setup_sandbox(Path(temp_dir))
        files_before = set(f.name for f in t_up.iterdir() if f.is_file())

        def fail_on_doc_check(event, **kwargs):
            if event == "post_doc_delete":
                raise RuntimeError("Simulated document row count mismatch: expected 9, got 8")

        failed = False
        try:
            execute_repair(dry_run=False, db_path=t_db, upload_dir=t_up, _failure_hook=fail_on_doc_check)
        except RuntimeError as re:
            failed = True
            assert "Simulated document row count mismatch" in str(re)
        assert failed, "Expected RuntimeError on document count mismatch"

        files_after = set(f.name for f in t_up.iterdir() if f.is_file())
        assert files_after == files_before, "Files not restored after document count failure"

        docs, chunks = get_counts(t_db)
        assert docs == EXPECTED_DOC_COUNT
        assert chunks == EXPECTED_CHUNK_COUNT
        print("[PASS] Document row-count failure handled: SQL rolled back, archived files restored to uploads.")
        gc.collect()

    # -----------------------------------------------------------------
    # TEST 11: Failure Injection - SQL Deletion Error with Auto-Rollback
    # -----------------------------------------------------------------
    print("\n--- TEST 11: Failure Injection - SQL Deletion Error with Auto-Rollback ---")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        t_db, t_up = setup_sandbox(Path(temp_dir))
        files_before = set(f.name for f in t_up.iterdir() if f.is_file())

        def fail_on_sql_syntax(event, **kwargs):
            if event == "pre_chunk_delete":
                # Execute invalid query to trigger sqlite OperationalError
                kwargs["cur"].execute("DELETE FROM non_existent_table_for_failure_test;")

        failed = False
        try:
            execute_repair(dry_run=False, db_path=t_db, upload_dir=t_up, _failure_hook=fail_on_sql_syntax)
        except sqlite3.OperationalError:
            failed = True
        assert failed, "Expected sqlite3.OperationalError on invalid SQL"

        files_after = set(f.name for f in t_up.iterdir() if f.is_file())
        assert files_after == files_before, "Files not restored after SQL failure"

        docs, chunks = get_counts(t_db)
        assert docs == EXPECTED_DOC_COUNT
        assert chunks == EXPECTED_CHUNK_COUNT
        print("[PASS] SQL failure handled: SQL rolled back, archived files restored to uploads.")
        gc.collect()

    # -----------------------------------------------------------------
    # TEST 12: Failure Injection - Commit Failure with Auto-Rollback
    # -----------------------------------------------------------------
    print("\n--- TEST 12: Failure Injection - Commit Failure with Auto-Rollback ---")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        t_db, t_up = setup_sandbox(Path(temp_dir))
        files_before = set(f.name for f in t_up.iterdir() if f.is_file())

        def fail_before_commit(event, **kwargs):
            if event == "pre_commit":
                raise sqlite3.OperationalError("Simulated database lock failure during commit")

        failed = False
        try:
            execute_repair(dry_run=False, db_path=t_db, upload_dir=t_up, _failure_hook=fail_before_commit)
        except sqlite3.OperationalError:
            failed = True
        assert failed, "Expected OperationalError before commit"

        files_after = set(f.name for f in t_up.iterdir() if f.is_file())
        assert files_after == files_before, "Files not restored after commit failure"

        docs, chunks = get_counts(t_db)
        assert docs == EXPECTED_DOC_COUNT
        assert chunks == EXPECTED_CHUNK_COUNT
        print("[PASS] Commit failure handled: SQL rolled back, archived files restored to uploads.")
        gc.collect()

    # -----------------------------------------------------------------
    # TEST 13: Destination Collision Prevention (Never Overwrite)
    # -----------------------------------------------------------------
    print("\n--- TEST 13: Destination Collision Prevention (Never Overwrite) ---")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        t_db, t_up = setup_sandbox(Path(temp_dir))
        doc1_name = "AAPL_EARNINGS_CALL_TRANSCRIPT_0df1e4e6.txt"

        collision_dir = t_up / "collision_test_archive"
        collision_dir.mkdir(parents=True, exist_ok=True)
        collision_dest = collision_dir / doc1_name
        sentinel_content = "CRITICAL SENTINEL: DO NOT OVERWRITE ME"
        collision_dest.write_text(sentinel_content)

        test_conn = sqlite3.connect(str(t_db))
        failed = False
        try:
            archive_upload_files(test_conn, collision_dir, upload_dir=t_up, dry_run=False)
        except FileExistsError as fee:
            failed = True
            assert "Archive collision" in str(fee)
        finally:
            test_conn.close()

        assert failed, "Expected FileExistsError on destination collision"
        assert collision_dest.read_text() == sentinel_content, "Existing file was overwritten!"
        assert (t_up / doc1_name).exists(), "Source file was removed despite collision!"
        print("[PASS] Collision prevention verified: existing files are never overwritten.")
        gc.collect()

    # -----------------------------------------------------------------
    # TEST 14: Dry-Run Absolute Immutability Verification
    # -----------------------------------------------------------------
    print("\n--- TEST 14: Dry-Run Absolute Immutability Verification ---")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        t_db, t_up = setup_sandbox(Path(temp_dir))

        db_hash_before = hashlib.sha256(t_db.read_bytes()).hexdigest()
        upload_hashes_before = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in t_up.iterdir() if f.is_file()}

        execute_repair(dry_run=True, db_path=t_db, upload_dir=t_up)

        db_hash_after = hashlib.sha256(t_db.read_bytes()).hexdigest()
        upload_hashes_after = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in t_up.iterdir() if f.is_file()}

        assert db_hash_after == db_hash_before, "DB binary hash changed during dry-run!"
        assert upload_hashes_after == upload_hashes_before, "Upload files modified during dry-run!"
        archive_dirs = list(t_up.glob("archive_*"))
        assert len(archive_dirs) == 0, f"Archive directory created in dry-run: {archive_dirs}"
        print("[PASS] Dry-run immutability verified: zero bytes or records modified.")
        gc.collect()

    print("\n==================================================================")
    print(" ALL 14 TESTS (REGRESSION & FAILURE INJECTION) PASSED!           ")
    print(" SAFE REPAIR IS FULLY ISOLATED, TRANSACTIONAL, AND SELF-HEALING.  ")
    print("==================================================================")

if __name__ == "__main__":
    run_all_tests()
