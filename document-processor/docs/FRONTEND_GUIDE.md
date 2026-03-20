# 🎨 Streamlit Frontend Guide

## 📋 Overview

A beautiful, modern Streamlit web interface for testing your PDF document processing system. No more Postman! 🚀

## ✨ Features

### 1. **📤 Upload PDF**
- Drag-and-drop or click to upload PDF files
- Real-time file size and name display
- Instant upload to backend

### 2. **📊 Live Progress Tracking**
- Real-time status updates (PENDING → PROCESSING → COMPLETED)
- Visual progress bar (0% to 100%)
- Auto-refresh option for hands-free monitoring
- Timeline with timestamps (created, started, completed)

### 3. **📥 View Results**
- **Text Tab**: Full extracted text with download button
- **Tables Tab**: Structured tables displayed as DataFrames
- **Images Tab**: Image metadata and locations
- **Metadata Tab**: Document properties (author, title, dates, etc.)

### 4. **📊 All Tasks Dashboard**
- View all tasks in one place
- Filter by status (Pending, Processing, Completed, Failed)
- Quick actions (View, Delete)
- Summary metrics (Total, Completed, Processing, Failed)

### 5. **ℹ️ About Page**
- System architecture explanation
- Processing flow diagram
- Tech stack details
- Quick links to API docs

## 🚀 Quick Start

### Step 1: Install Dependencies

```bash
cd document-processor
pip install -r requirements-frontend.txt
```

### Step 2: Start Backend (if not running)

Make sure your FastAPI backend is running on `http://localhost:8000`:

```bash
# Terminal 1: Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Terminal 2: Start FastAPI backend
uvicorn app.main:app --reload
```

### Step 3: Start SQS Worker (if not running)

```bash
# Terminal 3: Start the worker
python -m app.sqs_worker
```

### Step 4: Launch Streamlit Frontend

```bash
# Terminal 4: Start Streamlit
streamlit run streamlit_app.py
```

The app will open automatically in your browser at `http://localhost:8501`

## 🎯 Usage Guide

### Upload and Process a PDF

1. **Navigate to "📤 Upload PDF"** page (default)
2. **Click "Browse files"** or drag-and-drop a PDF
3. **Click "🚀 Start Processing"**
4. **Watch the progress** in real-time
5. **Click "📥 View Results"** when completed

### Monitor All Tasks

1. **Navigate to "📊 All Tasks"** page
2. **Use the filter** to show specific statuses
3. **Click "👁️ View"** to see task details
4. **Click "🗑️"** to delete a task

### Enable Auto-Refresh

- Check **"Auto-refresh status"** in the sidebar
- The page will automatically refresh every 3 seconds
- Perfect for monitoring long-running tasks

## 🎨 UI Features

### Modern Design Elements

- **Gradient headers** for visual appeal
- **Color-coded status badges**:
  - 🟡 PENDING (Yellow)
  - 🔵 PROCESSING (Blue)
  - 🟢 COMPLETED (Green)
  - 🔴 FAILED (Red)
- **Responsive layout** with columns
- **Interactive metrics** (pages, characters, tables, images)
- **Progress bars** with gradient animation

### User Experience

- **Real-time feedback** with spinners and success messages
- **Balloons celebration** on successful upload 🎈
- **Error messages** with helpful details
- **Collapsible sections** to reduce clutter
- **Download buttons** for extracted text
- **Tabbed interface** for different content types

## 🔧 Configuration

### Change Backend URL

Edit `streamlit_app.py` line 13:

```python
API_BASE_URL = "http://localhost:8000"  # Change this
```

### Customize Auto-Refresh Interval

Edit `show_upload_page()` and `show_all_tasks_page()` functions:

```python
time.sleep(3)  # Change from 3 seconds to your preference
```

## 📸 Screenshots (What You'll See)

### Upload Page
```
┌─────────────────────────────────────────────┐
│      📄 PDF Document Processor              │
│   Extract text, tables, and images from     │
│          PDFs using AI-powered LlamaParse   │
├─────────────────────────────────────────────┤
│ ✅ Connected to backend server              │
├─────────────────────────────────────────────┤
│ 📤 Upload PDF Document                      │
│ ┌─────────────────┐  ┌───────────────────┐ │
│ │ [Browse files]  │  │ 📋 Processing Steps│ │
│ │ Drag & drop here│  │ 1. Upload - S3    │ │
│ └─────────────────┘  │ 2. Queue - SQS    │ │
│                      │ 3. Extract - AI   │ │
│ 🚀 [Start Processing]│ 4. Store - DB     │ │
│                      │ 5. Complete ✅    │ │
│                      └───────────────────┘ │
├─────────────────────────────────────────────┤
│ 📊 Current Task Status                      │
│ Task ID: 123  Status: PROCESSING 50%       │
│ [Progress Bar: ████████████░░░░░░░░░ 50%]  │
└─────────────────────────────────────────────┘
```

### Results Page
```
┌─────────────────────────────────────────────┐
│ 📥 Extraction Results                       │
├─────────────────────────────────────────────┤
│ Pages: 10  |  Characters: 15,234           │
│ Tables: 3  |  Time: 12.4s                  │
├─────────────────────────────────────────────┤
│ [📝 Text] [📊 Tables] [🖼️ Images] [📋 Meta]│
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │ Extracted Text Content...               │ │
│ │ Lorem ipsum dolor sit amet...           │ │
│ │                                         │ │
│ └─────────────────────────────────────────┘ │
│ [💾 Download Text]                          │
└─────────────────────────────────────────────┘
```

## 🐛 Troubleshooting

### Backend Not Running

**Error**: `⚠️ Backend server is not running!`

**Solution**:
```bash
cd document-processor
uvicorn app.main:app --reload
```

### Port Already in Use

**Error**: `Address already in use`

**Solution**: Change Streamlit port:
```bash
streamlit run streamlit_app.py --server.port 8502
```

### CORS Error

**Error**: `Access-Control-Allow-Origin`

**Solution**: Check `app/main.py` has CORS middleware:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Task Not Found

**Error**: `❌ Task {task_id} not found`

**Cause**: Redis key expired or task deleted

**Solution**: Redis keys expire after 24 hours by default. Check your backend settings.

## 🎓 Advanced Tips

### 1. **Monitor Multiple Tasks**
- Open "All Tasks" page
- Enable auto-refresh
- You can see all tasks updating in real-time

### 2. **Test Error Handling**
- Upload a corrupted PDF
- Watch the status change to FAILED
- View the error message in the UI

### 3. **Performance Testing**
- Upload multiple PDFs quickly
- Watch them queue up in SQS
- Monitor processing order (FIFO)

### 4. **Database Verification**
- After completion, check pgAdmin
- Open `documents` table
- See the `result_text` and `status` columns

### 5. **Compare Extractors**
- Stop LlamaCloud API (disable API key)
- Upload a PDF
- It will fallback to PyPDF2
- Compare the quality in the Text tab

## 🚀 Next Steps

1. **Customize the UI**: Add your logo, change colors, add more metrics
2. **Add Authentication**: Implement user login with API keys
3. **Export Options**: Add PDF/JSON/CSV export for results
4. **Batch Upload**: Support multiple file uploads at once
5. **Charts & Analytics**: Add charts showing processing stats over time

## 📚 Related Files

- `streamlit_app.py` - Main frontend application
- `requirements-frontend.txt` - Frontend dependencies
- `app/main.py` - Backend API
- `app/sqs_worker.py` - Background worker

## 💡 Pro Tips

1. **Keep Auto-Refresh ON** when actively monitoring tasks
2. **Use the filter** on All Tasks page to focus on specific statuses
3. **Download extracted text** immediately for backup
4. **Check the About page** for system architecture details
5. **Use pgAdmin** alongside Streamlit to verify data persistence

---

**Enjoy your beautiful new frontend!** 🎉

If you have questions or need customization, just ask!
