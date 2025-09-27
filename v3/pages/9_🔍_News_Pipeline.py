import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
from streamlit import session_state

from core.news_pipeline import (
    BatchMode,
    NewsBatchProcessor,
    PipelineConfig,
    PipelineRequest,
    load_pipeline_config,
    ProgressEvent,
    ProgressReporter,
)
from core.news_pipeline.progress import StreamlitProgressReporter
from core.news_pipeline.repository import NewsPipelineRepository

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="News Pipeline - Ticker Candidate Generation",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 News Pipeline - Ticker Candidate Generation")
st.markdown("Масштабируемый пайплайн для генерации кандидатов-тикеров из новостей")

# Initialize session state
if "pipeline_initialized" not in session_state:
    session_state.pipeline_initialized = False
if "processor" not in session_state:
    session_state.processor = None
if "repository" not in session_state:
    session_state.repository = None
if "config" not in session_state:
    session_state.config = None
if "processing_status" not in session_state:
    session_state.processing_status = "idle"
if "last_metrics" not in session_state:
    session_state.last_metrics = None

# Initialize components
def migrate_companies_table(conn):
    """Add missing columns to companies table if needed."""
    try:
        cursor = conn.execute("PRAGMA table_info(companies)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        # Add missing columns
        if "name" not in existing_columns:
            conn.execute("ALTER TABLE companies ADD COLUMN name TEXT")
        if "isin" not in existing_columns:
            conn.execute("ALTER TABLE companies ADD COLUMN isin TEXT")
        if "figi" not in existing_columns:
            conn.execute("ALTER TABLE companies ADD COLUMN figi TEXT")
        if "created_at" not in existing_columns:
            conn.execute("ALTER TABLE companies ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        
        conn.commit()
        return True
    except Exception as e:
        st.warning(f"Could not migrate companies table: {e}")
        return False

def load_existing_tickers(repository):
    """Load existing tickers from companies table."""
    try:
        with repository.connect() as conn:
            # Migrate companies table first
            migrate_companies_table(conn)
            
            # Check if companies table exists and has data
            try:
                companies_count = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
                if companies_count > 0:
                    st.info(f"Found {companies_count} existing companies in database")
                    
                    # Check table structure first
                    cursor = conn.execute("PRAGMA table_info(companies)")
                    columns = [row[1] for row in cursor.fetchall()]
                    
                    # Build query based on available columns
                    select_fields = ["contract_code"]
                    if "name" in columns:
                        select_fields.append("name")
                    if "isin" in columns:
                        select_fields.append("isin")
                    if "figi" in columns:
                        select_fields.append("figi")
                    
                    query = f"""
                        SELECT {', '.join(select_fields)}
                        FROM companies 
                        WHERE contract_code IS NOT NULL AND contract_code != ''
                        ORDER BY contract_code
                    """
                    
                    companies = conn.execute(query).fetchall()
                    
                    # Insert into tickers table
                    inserted_count = 0
                    for row in companies:
                        # Extract fields based on available columns
                        contract_code = row[0]
                        name = row[1] if len(row) > 1 and "name" in columns else None
                        isin = row[2] if len(row) > 2 and "isin" in columns else None
                        figi = row[3] if len(row) > 3 and "figi" in columns else None
                        
                        # Create aliases from contract_code and name
                        aliases = [contract_code]
                        if name:
                            aliases.append(name)
                            # Add common variations
                            if "ПАО" in name:
                                aliases.append(name.replace("ПАО ", ""))
                            if "ООО" in name:
                                aliases.append(name.replace("ООО ", ""))
                        
                        # Insert into tickers table
                        conn.execute("""
                            INSERT OR IGNORE INTO tickers 
                            (ticker, name, aliases, isin, exchange, description)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            contract_code, 
                            name or contract_code, 
                            json.dumps(aliases, ensure_ascii=False), 
                            isin, 
                            "MOEX", 
                            f"Loaded from companies table: {name or contract_code}"
                        ))
                        inserted_count += 1
                    
                    conn.commit()
                    st.success(f"Loaded {inserted_count} tickers from companies table")
                    return True
                    
            except Exception as e:
                st.warning(f"Could not load from companies table: {e}")
                return False
                
    except Exception as exc:
        st.warning(f"Could not load existing tickers: {exc}")
        return False

def sync_with_news_system(repository):
    """Sync with existing news system."""
    try:
        with repository.connect() as conn:
            # Check if we have existing articles
            articles_count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
            
            if articles_count > 0:
                st.info(f"Found {articles_count} existing articles in database")
                
                # Check if articles are already processed by news pipeline
                processed_count = conn.execute("""
                    SELECT COUNT(*) FROM articles 
                    WHERE processed = 1 OR last_batch_id IS NOT NULL
                """).fetchone()[0]
                
                if processed_count == 0:
                    st.info("Articles are not yet processed by news pipeline")
                    return True
                else:
                    st.info(f"Found {processed_count} articles already processed by news pipeline")
                    return True
            else:
                st.info("No existing articles found in database")
                return False
                
    except Exception as exc:
        st.warning(f"Could not sync with news system: {exc}")
        return False

def create_test_candidates(repository):
    """Create test candidates for demonstration."""
    try:
        with repository.connect() as conn:
            # First ensure we have some articles and tickers
            articles_count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
            tickers_count = conn.execute("SELECT COUNT(*) FROM tickers").fetchone()[0]
            
            if articles_count == 0:
                # Create test articles
                conn.execute("""
                    INSERT INTO articles (title, body, language, published_at, source_id)
                    VALUES 
                    ('Test News 1', 'This is a test news about SBER bank', 'ru', datetime('now'), 1),
                    ('Test News 2', 'This is a test news about GAZP gas company', 'ru', datetime('now'), 1),
                    ('Test News 3', 'This is a test news about LKOH oil company', 'ru', datetime('now'), 1)
                """)
            
            if tickers_count == 0:
                # Create test tickers
                conn.execute("""
                    INSERT INTO tickers (ticker, name, aliases, exchange, description)
                    VALUES 
                    ('SBER', 'Сбербанк', '["Сбер", "Sberbank"]', 'MOEX', 'ПАО Сбербанк'),
                    ('GAZP', 'Газпром', '["Газпром", "Gazprom"]', 'MOEX', 'ПАО Газпром'),
                    ('LKOH', 'Лукойл', '["Лукойл", "Lukoil"]', 'MOEX', 'ПАО Лукойл')
                """)
            
            # Get article and ticker IDs
            articles = conn.execute("SELECT id FROM articles LIMIT 3").fetchall()
            tickers = conn.execute("SELECT id FROM tickers LIMIT 3").fetchall()
            
            if articles and tickers:
                # Create test candidates
                test_candidates = [
                    (articles[0][0], tickers[0][0], 0.85, 'fuzzy', 'test_batch_1'),
                    (articles[1][0], tickers[1][0], 0.75, 'substring', 'test_batch_1'),
                    (articles[2][0], tickers[2][0], 0.65, 'ner', 'test_batch_1'),
                ]
                
                for news_id, ticker_id, score, method, batch_id in test_candidates:
                    conn.execute("""
                        INSERT OR IGNORE INTO news_tickers 
                        (news_id, ticker_id, score, method, batch_id, created_at)
                        VALUES (?, ?, ?, ?, ?, datetime('now'))
                    """, (news_id, ticker_id, score, method, batch_id))
                
                conn.commit()
                return True
            else:
                st.error("Could not create test data: missing articles or tickers")
                return False
                
    except Exception as exc:
        st.error(f"Could not create test candidates: {exc}")
        return False

def show_news_statistics(repository):
    """Show news statistics."""
    try:
        with repository.connect() as conn:
            # Get basic statistics
            articles_count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
            processed_count = conn.execute("""
                SELECT COUNT(*) FROM articles 
                WHERE processed = 1 OR last_batch_id IS NOT NULL
            """).fetchone()[0]
            
            # Get recent articles
            recent_articles = conn.execute("""
                SELECT title, published_at, source_id
                FROM articles 
                ORDER BY COALESCE(published_at, ingested_at) DESC 
                LIMIT 5
            """).fetchall()
            
            # Get sources
            sources = conn.execute("""
                SELECT s.name, COUNT(a.id) as article_count
                FROM sources s
                LEFT JOIN articles a ON s.id = a.source_id
                GROUP BY s.id, s.name
                ORDER BY article_count DESC
            """).fetchall()
            
            st.subheader("News Statistics")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Articles", articles_count)
                st.metric("Processed Articles", processed_count)
                st.metric("Processing Rate", f"{(processed_count/articles_count*100):.1f}%" if articles_count > 0 else "0%")
            
            with col2:
                st.metric("Unprocessed Articles", articles_count - processed_count)
                st.metric("Sources", len(sources))
            
            if recent_articles:
                st.subheader("Recent Articles")
                for article in recent_articles:
                    title = article[0] or "No title"
                    published_at = article[1] or "No date"
                    source_id = article[2]
                    st.write(f"**{title}** - {published_at} (Source: {source_id})")
            
            if sources:
                st.subheader("Sources")
                for source in sources:
                    name = source[0] or "Unknown"
                    count = source[1] or 0
                    st.write(f"**{name}**: {count} articles")
                    
    except Exception as exc:
        st.error(f"Could not load news statistics: {exc}")

def migrate_existing_news(repository):
    """Migrate existing news from articles table to news pipeline format."""
    try:
        with repository.connect() as conn:
            # Check if we have existing articles
            articles_count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
            
            if articles_count > 0:
                st.info(f"Found {articles_count} existing articles in database")
                
                # Check if articles are already processed by news pipeline
                processed_count = conn.execute("""
                    SELECT COUNT(*) FROM articles 
                    WHERE processed = 1 OR last_batch_id IS NOT NULL
                """).fetchone()[0]
                
                if processed_count == 0:
                    st.info("Articles are not yet processed by news pipeline")
                    return True
                else:
                    st.info(f"Found {processed_count} articles already processed by news pipeline")
                    return True
            else:
                st.info("No existing articles found in database")
                return False
                
    except Exception as exc:
        st.warning(f"Could not check existing news: {exc}")
        return False

def create_sample_data(repository):
    """Create sample data if database is empty."""
    try:
        with repository.connect() as conn:
            # First try to load existing tickers from companies table
            if load_existing_tickers(repository):
                # Check for existing news
                migrate_existing_news(repository)
                return  # Successfully loaded existing tickers and news
            
            # Check if we have any tickers
            ticker_count = conn.execute("SELECT COUNT(*) FROM tickers").fetchone()[0]
            
            if ticker_count == 0:
                st.info("Creating sample tickers...")
                
                # Create sample tickers
                sample_tickers = [
                    ("SBER", "Сбербанк", '["Сбер", "Sberbank", "ПАО Сбербанк"]', "RU0009029540", "MOEX", "ПАО Сбербанк"),
                    ("GAZP", "Газпром", '["Газпром", "Gazprom", "ПАО Газпром"]', "RU0007661625", "MOEX", "ПАО Газпром"),
                    ("LKOH", "Лукойл", '["Лукойл", "Lukoil", "ПАО Лукойл"]', "RU0009024277", "MOEX", "ПАО Лукойл"),
                    ("GMKN", "Норникель", '["Норникель", "Norilsk Nickel", "ПАО ГМК Норильский никель"]', "RU0006752978", "MOEX", "ПАО ГМК Норильский никель"),
                    ("YNDX", "Яндекс", '["Яндекс", "Yandex", "ООО Яндекс"]', "NL0009805522", "MOEX", "ООО Яндекс"),
                ]
                
                for ticker, name, aliases, isin, exchange, description in sample_tickers:
                    conn.execute("""
                        INSERT OR IGNORE INTO tickers 
                        (ticker, name, aliases, isin, exchange, description)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (ticker, name, aliases, isin, exchange, description))
                
                conn.commit()
                st.success(f"Created {len(sample_tickers)} sample tickers")
            
            # Check if we have any sources
            source_count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
            
            if source_count == 0:
                st.info("Creating sample sources...")
                
                # Create sample sources
                conn.execute("""
                    INSERT OR IGNORE INTO sources (id, name, rss_url, website)
                    VALUES (1, 'Test Source', 'https://example.com/rss', 'https://example.com')
                """)
                
                conn.commit()
                st.success("Created sample source")
            
            # Check if we have any articles
            article_count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
            
            if article_count == 0:
                st.info("Creating sample articles...")
                
                # Create sample articles
                sample_articles = [
                    ("Сбербанк объявил о росте прибыли", "ПАО Сбербанк сообщил о значительном росте прибыли в отчетном периоде. Компания показала отличные результаты.", "2024-01-15T10:00:00Z", 1, "ru"),
                    ("Газпром увеличил добычу газа", "ПАО Газпром сообщило об увеличении добычи природного газа. Компания продолжает развиваться.", "2024-01-15T11:30:00Z", 1, "ru"),
                    ("Лукойл инвестирует в новые проекты", "ПАО Лукойл объявило о планах инвестирования в новые нефтегазовые проекты.", "2024-01-15T14:20:00Z", 1, "ru"),
                ]
                
                for title, body, published_at, source_id, language in sample_articles:
                    conn.execute("""
                        INSERT OR IGNORE INTO articles 
                        (title, body, published_at, source_id, language, processed)
                        VALUES (?, ?, ?, ?, ?, 0)
                    """, (title, body, published_at, source_id, language))
                
                conn.commit()
                st.success(f"Created {len(sample_articles)} sample articles")
                
    except Exception as exc:
        st.warning(f"Could not create sample data: {exc}")
        logger.warning("Sample data creation failed: %s", exc)

def initialize_pipeline():
    """Initialize the pipeline with configuration."""
    try:
        # Load configuration
        config = load_pipeline_config()
        
        # Initialize repository and processor
        repository = NewsPipelineRepository()
        
        # Ensure database schema exists
        repository.ensure_schema()
        
        # Create sample data if needed
        create_sample_data(repository)
        
        processor = NewsBatchProcessor(repository)
        processor.initialize(config)
        
        # Store in session state
        session_state.repository = repository
        session_state.processor = processor
        session_state.config = config
        session_state.pipeline_initialized = True
        
        st.success("Pipeline initialized successfully!")
        return True
        
    except Exception as exc:
        st.error(f"Failed to initialize pipeline: {exc}")
        logger.exception("Pipeline initialization failed")
        return False

# Initialize if not done
if not session_state.pipeline_initialized:
    with st.spinner("Initializing pipeline..."):
        initialize_pipeline()

if not session_state.pipeline_initialized:
    st.error("Pipeline initialization failed. Please check the logs.")
    st.stop()

# Main interface
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🚀 Batch Processing", "✅ Candidate Validation", "📊 Statistics", "⚙️ Configuration", "🔗 News Integration"])

with tab1:
    st.header("Batch Processing")
    
    # Processing mode selection
    col1, col2 = st.columns(2)
    
    with col1:
        mode = st.selectbox(
            "Processing Mode",
            options=[BatchMode.ONLY_UNPROCESSED, BatchMode.RECHECK_ALL, BatchMode.RECHECK_SELECTED_RANGE],
            format_func=lambda x: {
                BatchMode.ONLY_UNPROCESSED: "Only Unprocessed News",
                BatchMode.RECHECK_ALL: "Recheck All News",
                BatchMode.RECHECK_SELECTED_RANGE: "Recheck Selected Range",
            }[x],
            key="processing_mode_selectbox"
        )
    
    with col2:
        batch_size = st.number_input(
            "Batch Size",
            min_value=1,
            max_value=10000,
            value=session_state.config.batch_size,
            help="Number of news items to process in this batch",
            key="batch_size_input"
        )
    
    # Range selection for RECHECK_SELECTED_RANGE mode
    if mode == BatchMode.RECHECK_SELECTED_RANGE:
        col3, col4 = st.columns(2)
        with col3:
            range_start = st.date_input(
                "Start Date",
                value=datetime.now().date() - timedelta(days=7),
                help="Start date for news selection",
                key="range_start_date_input"
            )
        with col4:
            range_end = st.date_input(
                "End Date",
                value=datetime.now().date(),
                help="End date for news selection",
                key="range_end_date_input"
            )
    else:
        range_start = None
        range_end = None
    
    # Advanced options
    with st.expander("Advanced Options"):
        col5, col6 = st.columns(2)
        with col5:
            chunk_size = st.number_input(
                "Chunk Size",
                min_value=1,
                max_value=1000,
                value=session_state.config.chunk_size,
                help="Number of items to process in each chunk",
                key="chunk_size_input"
            )
        with col6:
            dry_run = st.checkbox(
                "Dry Run",
                value=False,
                help="Process without saving results to database",
                key="dry_run_checkbox"
            )
    
    # Processing controls
    col7, col8, col9 = st.columns(3)
    
    with col7:
        if st.button("🚀 Start Processing", disabled=session_state.processing_status == "running", key="start_processing_button"):
            if session_state.processing_status == "running":
                st.warning("Processing is already running!")
            else:
                # Create progress UI
                progress_bar = st.progress(0)
                status_text = st.empty()
                metrics_container = st.empty()
                
                # Create progress reporter
                progress_reporter = StreamlitProgressReporter(progress_bar, status_text)
                
                # Create request
                request = PipelineRequest(
                    mode=mode,
                    batch_size=batch_size,
                    range_start=range_start.isoformat() if range_start else None,
                    range_end=range_end.isoformat() if range_end else None,
                    operator=st.session_state.get("user_name", "unknown"),
                    dry_run=dry_run,
                )
                
                # Update config with user settings
                config = session_state.config.with_overrides(
                    chunk_size=chunk_size,
                    dry_run=dry_run,
                )
                session_state.config = config
                session_state.processor.initialize(config)
                
                # Start processing
                session_state.processing_status = "running"
                
                try:
                    with st.spinner("Processing news items..."):
                        metrics = session_state.processor.process_batch(
                            request,
                            progress_reporter=progress_reporter,
                        )
                    
                    session_state.last_metrics = metrics
                    session_state.processing_status = "completed"
                    
                    # Display results
                    st.success("Processing completed successfully!")
                    
                    # Show metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total News", metrics.total_news)
                    with col2:
                        st.metric("Processed", metrics.processed_news)
                    with col3:
                        st.metric("Candidates Generated", metrics.candidates_generated)
                    with col4:
                        st.metric("Auto Applied", metrics.auto_applied)
                    
                    col5, col6, col7, col8 = st.columns(4)
                    with col5:
                        st.metric("Skipped Duplicates", metrics.skipped_duplicates)
                    with col6:
                        st.metric("Errors", metrics.errors)
                    with col7:
                        st.metric("Duration (s)", f"{metrics.duration_seconds:.2f}")
                    with col8:
                        st.metric("Chunks", metrics.chunk_count)
                    
                    # Show detailed metrics
                    if st.checkbox("Show Detailed Metrics"):
                        st.json(metrics.as_dict())
                
                except Exception as exc:
                    session_state.processing_status = "failed"
                    st.error(f"Processing failed: {exc}")
                    logger.exception("Batch processing failed")
    
    with col8:
        if st.button("⏹️ Stop Processing", disabled=session_state.processing_status != "running", key="stop_processing_button"):
            # This would need to be implemented in the processor
            st.warning("Stop functionality not yet implemented")
    
    with col9:
        if st.button("🔄 Reset Status", key="reset_status_button"):
            session_state.processing_status = "idle"
            session_state.last_metrics = None
            st.rerun()
    
    # Show current status
    if session_state.processing_status == "running":
        st.info("🔄 Processing is currently running...")
    elif session_state.processing_status == "completed":
        st.success("✅ Processing completed successfully!")
    elif session_state.processing_status == "failed":
        st.error("❌ Processing failed!")

with tab2:
    st.header("Candidate Validation")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        min_score = st.slider(
            "Minimum Score",
            min_value=0.0,
            max_value=1.0,
            value=0.6,
            step=0.05,
            help="Minimum confidence score for candidates",
            key="validation_min_score_slider"
        )
    
    with col2:
        only_unconfirmed = st.checkbox(
            "Only Unconfirmed",
            value=True,
            help="Show only unconfirmed candidates",
            key="validation_only_unconfirmed_checkbox"
        )
    
    with col3:
        limit = st.number_input(
            "Limit",
            min_value=1,
            max_value=1000,
            value=100,
            help="Maximum number of candidates to show",
            key="candidates_limit_input"
        )
    
    # Database status check
    with session_state.repository.connect() as conn:
        # Check if we have any data in the pipeline tables
        news_tickers_count = conn.execute("SELECT COUNT(*) FROM news_tickers").fetchone()[0]
        tickers_count = conn.execute("SELECT COUNT(*) FROM tickers").fetchone()[0]
        articles_count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        confirmed_count = conn.execute("SELECT COUNT(*) FROM news_tickers WHERE confirmed = 1").fetchone()[0]
        
        st.write("**Database Status:**")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("News-Tickers", news_tickers_count)
        with col2:
            st.metric("Tickers", tickers_count)
        with col3:
            st.metric("Articles", articles_count)
        with col4:
            st.metric("Confirmed", confirmed_count)
        
        # Show integration status
        if confirmed_count > 0:
            st.success(f"✅ Интеграция готова! {confirmed_count} подтвержденных связей новостей с тикерами.")
            
            # Show some examples
            examples = conn.execute("""
                SELECT a.title, t.ticker, nt.score, nt.method
                FROM news_tickers nt
                JOIN articles a ON a.id = nt.news_id
                JOIN tickers t ON t.id = nt.ticker_id
                WHERE nt.confirmed = 1
                LIMIT 3
            """).fetchall()
            
            if examples:
                st.write("**Примеры подтвержденных связей:**")
                for row in examples:
                    st.write(f"• {row['title'][:60]}... → {row['ticker']} (score: {row['score']:.2f})")
        else:
            st.warning("⚠️ Нет подтвержденных связей. Запустите обработку и подтвердите кандидатов.")
    
    # Create test data if needed
    if news_tickers_count == 0:
        st.warning("No candidates found in database. You may need to run batch processing first.")
        if st.button("🧪 Create Test Data", key="create_test_data_button"):
            with st.spinner("Creating test data..."):
                create_test_candidates(session_state.repository)
                st.success("Test data created! Refresh candidates to see them.")
                st.rerun()
    
    # Load candidates
    if st.button("🔄 Refresh Candidates", key="refresh_candidates_button"):
        # Clear cache to force refresh
        if 'candidates_data' in st.session_state:
            del st.session_state.candidates_data
        st.rerun()
    
    # Load candidates from cache or database
    if 'candidates_data' not in st.session_state:
        with st.spinner("Loading candidates..."):
            candidates = session_state.repository.fetch_pending_candidates(
                min_score=min_score,
                only_unconfirmed=only_unconfirmed,
                limit=limit,
            )
            st.session_state.candidates_data = candidates
    else:
        candidates = st.session_state.candidates_data
    
    if candidates:
        # Convert to DataFrame with proper column names
        df = pd.DataFrame(candidates)
        
        # Set proper column names based on SQL query structure
        column_names = [
            'id', 'news_id', 'ticker_id', 'score', 'method', 'created_at', 'updated_at',
            'confirmed', 'confirmed_by', 'confirmed_at', 'batch_id', 'auto_suggest',
            'history', 'metadata', 'ticker', 'name', 'title', 'published_at'
        ]
        df.columns = column_names
        
        # Debug: Show column names and sample data
        st.write("**Debug Info:**")
        st.write(f"Columns: {list(df.columns)}")
        st.write(f"DataFrame shape: {df.shape}")
        if len(df) > 0:
            st.write("Sample row:", df.iloc[0].to_dict())
            st.write("Data types:", df.dtypes.to_dict())
            st.write("Null values:", df.isnull().sum().to_dict())
        
        # Display candidates
        st.subheader(f"Found {len(df)} candidates")
        
        # Show confirmation status
        confirmed_count = len(df[df['confirmed'] == 1])
        rejected_count = len(df[df['confirmed'] == -1])
        unconfirmed_count = len(df[df['confirmed'] == 0])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Confirmed", confirmed_count)
        with col2:
            st.metric("Rejected", rejected_count)
        with col3:
            st.metric("Unconfirmed", unconfirmed_count)
        
        # Batch actions
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✅ Confirm All High Score", key="confirm_all_high_score_button"):
                high_score_threshold = st.slider(
                    "High Score Threshold",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.85,
                    step=0.05,
                    key="confirm_high_score_threshold_slider"
                )
                high_score_candidates = df[df['score'] >= high_score_threshold]
                if len(high_score_candidates) > 0:
                    for idx, candidate in high_score_candidates.iterrows():
                        candidate_dict = candidate.to_dict()
                        candidate_id = candidate_dict.get('id', 0)
                        session_state.repository.update_confirmation(
                            candidate_id,
                            confirmed=1,
                            operator=st.session_state.get("user_name", "unknown"),
                        )
                    st.success(f"Confirmed {len(high_score_candidates)} high-score candidates")
                    # Clear cache and refresh
                    if 'candidates_data' in st.session_state:
                        del st.session_state.candidates_data
                    st.rerun()
        
        with col2:
            if st.button("❌ Reject All Low Score", key="reject_all_low_score_button"):
                low_score_threshold = st.slider(
                    "Low Score Threshold",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.3,
                    step=0.05,
                    key="reject_low_score_threshold_slider"
                )
                low_score_candidates = df[df['score'] < low_score_threshold]
                if len(low_score_candidates) > 0:
                    for idx, candidate in low_score_candidates.iterrows():
                        candidate_dict = candidate.to_dict()
                        candidate_id = candidate_dict.get('id', 0)
                        session_state.repository.update_confirmation(
                            candidate_id,
                            confirmed=-1,
                            operator=st.session_state.get("user_name", "unknown"),
                        )
                    st.success(f"Rejected {len(low_score_candidates)} low-score candidates")
                    # Clear cache and refresh
                    if 'candidates_data' in st.session_state:
                        del st.session_state.candidates_data
                    st.rerun()
        
        with col3:
            if st.button("🔄 Reset All", key="reset_all_button"):
                if st.checkbox("Are you sure?", key="reset_all_confirm_checkbox"):
                    for idx, candidate in df.iterrows():
                        candidate_dict = candidate.to_dict()
                        candidate_id = candidate_dict.get('id', 0)
                        session_state.repository.update_confirmation(
                            candidate_id,
                            confirmed=0,
                            operator=st.session_state.get("user_name", "unknown"),
                        )
                    st.success("Reset all candidates to unconfirmed")
                    # Clear cache and refresh
                    if 'candidates_data' in st.session_state:
                        del st.session_state.candidates_data
                    st.rerun()
        
        # Individual candidate validation
        st.subheader("Individual Validation")
        
        for idx, candidate in df.iterrows():
            # Convert pandas Series to dict for easier access
            candidate_dict = candidate.to_dict()
            
            # Safe access to fields with fallbacks
            ticker = candidate_dict.get('ticker', 'Unknown')
            score = candidate_dict.get('score', 0.0)
            title = candidate_dict.get('title', 'No title')
            method = candidate_dict.get('method', 'Unknown')
            candidate_id = candidate_dict.get('id', 0)
            
            # Create unique keys using both idx and candidate_id
            unique_key_suffix = f"{idx}_{candidate_id}"
            
            with st.expander(f"Candidate {idx + 1}: {ticker} (Score: {score:.3f})"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**News:** {title[:100]}...")
                    st.write(f"**Ticker:** {ticker}")
                    st.write(f"**Score:** {score:.3f}")
                    st.write(f"**Method:** {method}")
                
                with col2:
                    if st.button(f"✅ Confirm", key=f"confirm_{unique_key_suffix}"):
                        try:
                            st.write(f"DEBUG: Confirming candidate {candidate_id}")
                            session_state.repository.update_confirmation(
                                candidate_id,
                                confirmed=1,
                                operator=st.session_state.get("user_name", "unknown"),
                            )
                            st.success(f"Candidate {candidate_id} confirmed!")
                            # Clear cache and refresh
                            if 'candidates_data' in st.session_state:
                                del st.session_state.candidates_data
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error confirming candidate: {e}")
                            st.write(f"DEBUG: Exception details: {type(e).__name__}: {e}")
                
                with col3:
                    if st.button(f"❌ Reject", key=f"reject_{unique_key_suffix}"):
                        try:
                            st.write(f"DEBUG: Rejecting candidate {candidate_id}")
                            session_state.repository.update_confirmation(
                                candidate_id,
                                confirmed=-1,
                                operator=st.session_state.get("user_name", "unknown"),
                            )
                            st.success(f"Candidate {candidate_id} rejected!")
                            # Clear cache and refresh
                            if 'candidates_data' in st.session_state:
                                del st.session_state.candidates_data
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error rejecting candidate: {e}")
                            st.write(f"DEBUG: Exception details: {type(e).__name__}: {e}")
    else:
        st.info("No candidates found matching the criteria")

with tab3:
    st.header("Statistics")
    
    # Load statistics
    if st.button("🔄 Refresh Statistics", key="refresh_statistics_button"):
        with st.spinner("Loading statistics..."):
            # Get basic counts
            with session_state.repository.connect() as conn:
                # Total news
                total_news = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
                
                # Processed news
                processed_news = conn.execute("SELECT COUNT(*) FROM articles WHERE processed = 1").fetchone()[0]
                
                # Total candidates
                total_candidates = conn.execute("SELECT COUNT(*) FROM news_tickers").fetchone()[0]
                
                # Confirmed candidates
                confirmed_candidates = conn.execute("SELECT COUNT(*) FROM news_tickers WHERE confirmed = 1").fetchone()[0]
                
                # Rejected candidates
                rejected_candidates = conn.execute("SELECT COUNT(*) FROM news_tickers WHERE confirmed = -1").fetchone()[0]
                
                # Pending candidates
                pending_candidates = conn.execute("SELECT COUNT(*) FROM news_tickers WHERE confirmed = 0").fetchone()[0]
                
                # Processing runs
                processing_runs = conn.execute("SELECT COUNT(*) FROM processing_runs").fetchone()[0]
            
            # Display statistics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total News", total_news)
                st.metric("Processed News", processed_news)
                st.metric("Processing Progress", f"{(processed_news/total_news*100):.1f}%" if total_news > 0 else "0%")
            
            with col2:
                st.metric("Total Candidates", total_candidates)
                st.metric("Confirmed", confirmed_candidates)
                st.metric("Rejected", rejected_candidates)
            
            with col3:
                st.metric("Pending", pending_candidates)
                st.metric("Processing Runs", processing_runs)
                st.metric("Confirmation Rate", f"{(confirmed_candidates/(confirmed_candidates+rejected_candidates)*100):.1f}%" if (confirmed_candidates+rejected_candidates) > 0 else "0%")
            
            # Score distribution
            st.subheader("Score Distribution")
            with session_state.repository.connect() as conn:
                score_data = conn.execute("""
                    SELECT 
                        CASE 
                            WHEN score >= 0.9 THEN '0.9-1.0'
                            WHEN score >= 0.8 THEN '0.8-0.9'
                            WHEN score >= 0.7 THEN '0.7-0.8'
                            WHEN score >= 0.6 THEN '0.6-0.7'
                            ELSE '0.0-0.6'
                        END as score_range,
                        COUNT(*) as count
                    FROM news_tickers
                    GROUP BY score_range
                    ORDER BY score_range DESC
                """).fetchall()
                
                if score_data:
                    score_df = pd.DataFrame(score_data, columns=['Score Range', 'Count'])
                    st.bar_chart(score_df.set_index('Score Range'))
            
            # Recent processing runs
            st.subheader("Recent Processing Runs")
            with session_state.repository.connect() as conn:
                runs_data = conn.execute("""
                    SELECT 
                        batch_id,
                        mode,
                        batch_size_requested,
                        batch_size_actual,
                        started_at,
                        finished_at,
                        status,
                        metrics
                    FROM processing_runs
                    ORDER BY started_at DESC
                    LIMIT 10
                """).fetchall()
                
                if runs_data:
                    runs_df = pd.DataFrame(runs_data, columns=[
                        'Batch ID', 'Mode', 'Requested', 'Actual', 'Started', 'Finished', 'Status', 'Metrics'
                    ])
                    st.dataframe(runs_df, use_container_width=True)

with tab4:
    st.header("Configuration")
    
    # Current configuration
    st.subheader("Current Configuration")
    config_dict = session_state.config.as_dict()
    
    # Editable configuration
    new_config = {}
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_config['batch_size'] = st.number_input(
            "Batch Size",
            min_value=1,
            max_value=10000,
            value=config_dict['batch_size'],
            help="Default batch size for processing",
            key="config_batch_size_input"
        )
        
        new_config['chunk_size'] = st.number_input(
            "Chunk Size",
            min_value=1,
            max_value=1000,
            value=config_dict['chunk_size'],
            help="Number of items to process in each chunk",
            key="config_chunk_size_input"
        )
        
        new_config['auto_apply_threshold'] = st.slider(
            "Auto Apply Threshold",
            min_value=0.0,
            max_value=1.0,
            value=config_dict['auto_apply_threshold'],
            step=0.05,
            help="Score threshold for automatic candidate confirmation",
            key="config_auto_apply_threshold_slider"
        )
        
        new_config['review_lower_threshold'] = st.slider(
            "Review Lower Threshold",
            min_value=0.0,
            max_value=1.0,
            value=config_dict['review_lower_threshold'],
            step=0.05,
            help="Minimum score for candidates to be considered for review",
            key="config_review_lower_threshold_slider"
        )
    
    with col2:
        new_config['fuzzy_threshold'] = st.number_input(
            "Fuzzy Threshold",
            min_value=0,
            max_value=100,
            value=config_dict['fuzzy_threshold'],
            help="Fuzzy matching threshold (0-100)",
            key="config_fuzzy_threshold_input"
        )
        
        new_config['cos_candidate_threshold'] = st.slider(
            "Cosine Candidate Threshold",
            min_value=0.0,
            max_value=1.0,
            value=config_dict['cos_candidate_threshold'],
            step=0.05,
            help="Cosine similarity threshold for candidate generation",
            key="config_cos_candidate_threshold_slider"
        )
        
        new_config['cos_auto_threshold'] = st.slider(
            "Cosine Auto Threshold",
            min_value=0.0,
            max_value=1.0,
            value=config_dict['cos_auto_threshold'],
            step=0.05,
            help="Cosine similarity threshold for automatic confirmation",
            key="config_cos_auto_threshold_slider"
        )
        
        new_config['auto_apply_confirm'] = st.checkbox(
            "Auto Apply Confirm",
            value=config_dict['auto_apply_confirm'],
            help="Automatically confirm candidates above auto-apply threshold",
            key="config_auto_apply_confirm_checkbox"
        )
    
    # News integration moved to separate tab
    
    # Ticker management
    st.subheader("Ticker Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Reload Tickers from Companies", key="reload_tickers_button"):
            with st.spinner("Reloading tickers from companies table..."):
                if load_existing_tickers(session_state.repository):
                    # Reinitialize processor to load new tickers
                    session_state.processor.initialize(session_state.config)
                    st.success("Tickers reloaded successfully!")
                    st.rerun()
                else:
                    st.error("Failed to reload tickers")
    
    with col2:
        with session_state.repository.connect() as conn:
            ticker_count = conn.execute("SELECT COUNT(*) FROM tickers").fetchone()[0]
            st.metric("Total Tickers", ticker_count)
    
    # Save configuration
    if st.button("💾 Save Configuration", key="save_configuration_button"):
        try:
            # Update configuration
            updated_config = session_state.config.with_overrides(**new_config)
            session_state.config = updated_config
            
            # Reinitialize processor with new config
            session_state.processor.initialize(updated_config)
            
            st.success("Configuration saved and applied!")
            st.rerun()
            
        except Exception as exc:
            st.error(f"Failed to save configuration: {exc}")
    
    # Export/Import configuration
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📤 Export Configuration", key="export_configuration_button"):
            config_json = json.dumps(config_dict, indent=2)
            st.download_button(
                label="Download Configuration",
                data=config_json,
                file_name=f"news_pipeline_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with col2:
        uploaded_file = st.file_uploader("📥 Import Configuration", type=['json'])
        if uploaded_file is not None:
            try:
                imported_config = json.load(uploaded_file)
                st.success("Configuration imported successfully!")
                st.json(imported_config)
                
                if st.button("Apply Imported Configuration", key="apply_imported_configuration_button"):
                    updated_config = session_state.config.with_overrides(**imported_config)
                    session_state.config = updated_config
                    session_state.processor.initialize(updated_config)
                    st.success("Imported configuration applied!")
                    st.rerun()
                    
            except Exception as exc:
                st.error(f"Failed to import configuration: {exc}")

with tab5:
    st.header("News Integration")
    
    st.markdown("""
    ### Интеграция с существующей системой новостей
    
    Пайплайн новостей интегрирован с существующей системой новостей (страница "🗞️ News").
    Новости собираются через RSS-парсер и сохраняются в таблицу `articles`, а затем обрабатываются
    пайплайном для генерации кандидатов-тикеров.
    """)
    
    # News integration controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Sync with News System", key="sync_news_button"):
            with st.spinner("Syncing with existing news system..."):
                if sync_with_news_system(session_state.repository):
                    st.success("News system synchronized successfully!")
                    st.rerun()
                else:
                    st.error("Failed to sync with news system")
    
    with col2:
        if st.button("📊 View News Statistics", key="view_news_stats_button"):
            show_news_statistics(session_state.repository)
    
    with col3:
        if st.button("🔗 Open News Page", key="open_news_page_button"):
            st.info("Перейдите на страницу '🗞️ News' для управления источниками и просмотра новостей")
    
    # News statistics
    st.subheader("Current News Status")
    
    with session_state.repository.connect() as conn:
        articles_count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        processed_count = conn.execute("""
            SELECT COUNT(*) FROM articles 
            WHERE processed = 1 OR last_batch_id IS NOT NULL
        """).fetchone()[0]
        sources_count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Articles", articles_count)
    with col2:
        st.metric("Processed Articles", processed_count)
    with col3:
        st.metric("Unprocessed Articles", articles_count - processed_count)
    with col4:
        st.metric("Sources", sources_count)
    
    # Workflow explanation
    st.subheader("Workflow")
    
    st.markdown("""
    #### 1. Сбор новостей
    - Перейдите на страницу "🗞️ News"
    - Нажмите "Запустить парсер сейчас" для сбора новостей из RSS-лент
    - Новости сохраняются в таблицу `articles`
    
    #### 2. Обработка пайплайном
    - Вернитесь на эту страницу "🔍 News Pipeline"
    - Выберите режим "Only Unprocessed News"
    - Нажмите "🚀 Start Processing" для генерации кандидатов-тикеров
    - Кандидаты сохраняются в таблицу `news_tickers`
    
    #### 3. Валидация кандидатов
    - Перейдите на вкладку "✅ Candidate Validation"
    - Просмотрите и подтвердите/отклоните кандидатов
    - Подтвержденные кандидаты становятся доступными для анализа
    
    #### 4. Просмотр результатов
    - Вернитесь на страницу "🗞️ News" для просмотра новостей с привязанными тикерами
    - Используйте "Сводка за день" для анализа упоминаний тикеров
    """)
    
    # Recent articles preview
    if articles_count > 0:
        st.subheader("Recent Articles Preview")
        
        with session_state.repository.connect() as conn:
            recent_articles = conn.execute("""
                SELECT a.title, a.published_at, s.name as source_name, a.processed
                FROM articles a
                LEFT JOIN sources s ON a.source_id = s.id
                ORDER BY COALESCE(a.published_at, a.ingested_at) DESC 
                LIMIT 5
            """).fetchall()
        
        for article in recent_articles:
            title = article[0] or "No title"
            published_at = article[1] or "No date"
            source_name = article[2] or "Unknown source"
            processed = article[3] or 0
            
            status = "✅ Processed" if processed else "⏳ Pending"
            
            with st.expander(f"{title} - {status}"):
                st.write(f"**Source:** {source_name}")
                st.write(f"**Published:** {published_at}")
                st.write(f"**Status:** {status}")

# Footer
st.markdown("---")
st.markdown("**News Pipeline v1.0** - Масштабируемый пайплайн для генерации кандидатов-тикеров")
