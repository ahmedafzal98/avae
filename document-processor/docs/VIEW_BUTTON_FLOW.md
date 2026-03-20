# 👁️ View Button - Complete Flow & Display Guide

## What Happens When You Click "View" Button

### Step 1: Click "View" on All Tasks Page
When you click **"👁️ View"** on any task in the "📊 All Tasks" page:

```
📊 All Tasks Page
┌─────────────────────────────────────────────┐
│ document.pdf     │ COMPLETED │ 100% │ 👁️ 🗑️ │
└─────────────────────────────────────────────┘
                                    ↑
                                Click here
```

### Step 2: Navigation & Redirect
The system:
1. Saves the task ID: `st.session_state.uploaded_task_id = task_id`
2. Sets redirect flag: `st.session_state.view_task_redirect = True`
3. Navigates to **"📤 Upload PDF"** page
4. Shows detailed task status

---

## 📊 What You See After Clicking "View"

### Phase 1: Task Status Card (Always Shown)

```
┌─────────────────────────────────────────────────────────┐
│                📊 Current Task Status                   │
├─────────────────────────────────────────────────────────┤
│ Task ID: 10  │ Status: COMPLETED ✅ │ Progress: 100%  │
│              │ File: document.pdf                      │
├─────────────────────────────────────────────────────────┤
```

**4 Metric Cards Displayed:**
1. **Task ID** - The database ID (e.g., `10`)
2. **Status** - Color-coded badge:
   - 🟡 PENDING (Yellow)
   - 🔵 PROCESSING (Blue)
   - 🟢 COMPLETED (Green)
   - 🔴 FAILED (Red)
3. **Progress** - Percentage (0% to 100%)
4. **File** - Original filename

---

### Phase 2: Progress Bar & Status Messages (For Active Tasks)

**If status is PENDING or PROCESSING:**

```
[████████████████░░░░░░░░ 60%]

📄 Extracting text... Using LlamaParse AI to extract content
```

**Detailed Progress Messages Based on Percentage:**
- **0-10%**: "📥 Downloading from S3... Fetching PDF file from cloud storage."
- **10-20%**: "💾 Preparing file... Saving to temporary location for processing."
- **20-40%**: "📄 Extracting text... Using LlamaParse AI to extract content (this may take a moment)."
- **40-60%**: "📊 Extracting tables... Identifying and structuring table data."
- **60-80%**: "🖼️ Extracting images... Finding and processing embedded images."
- **80-90%**: "ℹ️ Extracting metadata... Reading document properties and information."
- **90-100%**: "💾 Finalizing... Saving results to PostgreSQL and Redis cache."

---

### Phase 3: Timeline Expander (Always Available)

```
⏰ Timeline (Click to expand)
├─────────────────────────────────────────────┐
│ Created At      │ Started At    │ Completed │
│ 2026-02-17      │ 2026-02-17   │ 2026-02-17│
│ 10:30:15        │ 10:30:18     │ 10:30:25  │
└─────────────────────────────────────────────┘
```

Shows:
- **Created At** - When task was uploaded
- **Started At** - When worker began processing
- **Completed At** - When processing finished

---

### Phase 4: Results Section (For COMPLETED Tasks)

**If status is COMPLETED, you see:**

```
✅ Processing completed!

[📥 View Results] ← Click this button
```

---

## 📥 What "View Results" Shows (After Clicking)

When you click **"📥 View Results"** on a completed task:

### Summary Metrics Bar

```
┌────────────────────────────────────────────────┐
│ Pages: 5 │ Characters: 15,234 │ Tables: 3 │ Time: 12.4s │
└────────────────────────────────────────────────┘
```

**4 Metric Cards:**
1. **Pages** - Total page count
2. **Characters** - Total character count in extracted text
3. **Tables** - Number of tables found
4. **Time** - Extraction time in seconds

---

### Tabbed Interface (4 Tabs)

## Tab 1: 📝 Text

```
┌───────────────────────────────────────────────────┐
│                 📝 Extracted Text                 │
├───────────────────────────────────────────────────┤
│ ┌───────────────────────────────────────────────┐ │
│ │ Full Text Content                             │ │
│ │                                               │ │
│ │ Lorem ipsum dolor sit amet, consectetur       │ │
│ │ adipiscing elit. Sed do eiusmod tempor        │ │
│ │ incididunt ut labore et dolore magna aliqua.  │ │
│ │                                               │ │
│ │ [Scrollable text area - 400px height]        │ │
│ │                                               │ │
│ │ ...more content...                            │ │
│ └───────────────────────────────────────────────┘ │
│                                                   │
│ [💾 Download Text]  ← Download as .txt file      │
└───────────────────────────────────────────────────┘
```

**Features:**
- Full extracted text from LlamaParse
- Scrollable text area (400px height)
- **Download button** to save as `.txt` file
- Shows character count
- If no text: Shows "No text content extracted"

---

## Tab 2: 📊 Tables

```
┌───────────────────────────────────────────────────┐
│                📊 Extracted Tables                │
├───────────────────────────────────────────────────┤
│ Table 1 (Page 2)                                  │
│ ┌─────────────┬──────────────┬─────────────────┐ │
│ │ Product     │ Quantity     │ Price           │ │
│ ├─────────────┼──────────────┼─────────────────┤ │
│ │ Widget A    │ 100          │ $10.00          │ │
│ │ Widget B    │ 50           │ $15.50          │ │
│ │ Widget C    │ 75           │ $8.25           │ │
│ └─────────────┴──────────────┴─────────────────┘ │
├───────────────────────────────────────────────────┤
│ Table 2 (Page 4)                                  │
│ ┌─────────────┬──────────────┬─────────────────┐ │
│ │ ...                                           │ │
│ └─────────────┴──────────────┴─────────────────┘ │
└───────────────────────────────────────────────────┘
```

**Features:**
- Shows each table with page number
- Displayed as interactive DataFrames (sortable, searchable)
- Falls back to JSON if DataFrame conversion fails
- Shows "No tables found in the document" if empty

---

## Tab 3: 🖼️ Images

```
┌───────────────────────────────────────────────────┐
│               🖼️ Extracted Images                 │
├───────────────────────────────────────────────────┤
│ ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│ │ Image 1 │  │ Image 2 │  │ Image 3 │           │
│ │ Page 1  │  │ Page 2  │  │ Page 3  │           │
│ │ Format: │  │ Format: │  │ Format: │           │
│ │ JPEG    │  │ PNG     │  │ JPEG    │           │
│ │ Size:   │  │ Size:   │  │ Size:   │           │
│ │ 800x600 │  │ 1024x768│  │ 640x480 │           │
│ └─────────┘  └─────────┘  └─────────┘           │
│                                                   │
│ ┌─────────┐  ┌─────────┐                        │
│ │ Image 4 │  │ Image 5 │                        │
│ │ Page 4  │  │ Page 5  │                        │
│ │ ...     │  │ ...     │                        │
│ └─────────┘  └─────────┘                        │
└───────────────────────────────────────────────────┘
```

**Features:**
- Grid layout (3 columns)
- Shows for each image:
  - Image number
  - Page number
  - Format (JPEG, PNG, etc.)
  - Dimensions (width x height)
- Shows "No images found in the document" if empty

---

## Tab 4: 📋 Metadata

```
┌───────────────────────────────────────────────────┐
│              📋 Document Metadata                 │
├───────────────────────────────────────────────────┤
│ ┌─────────────────────┬───────────────────────┐  │
│ │ Document Info       │ Technical Info        │  │
│ ├─────────────────────┼───────────────────────┤  │
│ │ Title: Annual Report│ Producer: Adobe PDF   │  │
│ │ Author: John Smith  │ Created: 2026-01-15   │  │
│ │ Subject: Finance    │ Modified: 2026-02-01  │  │
│ │ Creator: MS Word    │                       │  │
│ └─────────────────────┴───────────────────────┘  │
└───────────────────────────────────────────────────┘
```

**Features:**
- Two-column layout
- **Left Column (Document Info):**
  - Title
  - Author
  - Subject
  - Creator
- **Right Column (Technical Info):**
  - Producer (software that created PDF)
  - Creation date
  - Modification date
- Shows "No metadata available" if empty

---

## 🗑️ Action Buttons (Always Available)

At the bottom of the task status view:

```
┌─────────────────────────────────────────┐
│ [🔄 Refresh Status] │ [🗑️ Delete Task] │
└─────────────────────────────────────────┘
```

1. **🔄 Refresh Status** - Manually refresh task status
2. **🗑️ Delete Task** - Delete task from all systems (S3, Redis, PostgreSQL)

---

## 📱 Complete Visual Flow

### Starting Point: All Tasks Page

```
📊 All Tasks Page
┌─────────────────────────────────────────────────────┐
│ Total: 5  │  Completed: 3  │  Processing: 1  │ ... │
├─────────────────────────────────────────────────────┤
│ Filter: [All ▼]                                     │
├─────────────────────────────────────────────────────┤
│ report.pdf        │ ✅ COMPLETED │ 100% │ 👁️ │ 🗑️│
│ invoice.pdf       │ 🔵 PROCESSING│  60% │ 👁️ │ 🗑️│
│ contract.pdf      │ ✅ COMPLETED │ 100% │ 👁️ │ 🗑️│
└─────────────────────────────────────────────────────┘
                                            ↑ Click View
```

### After Clicking View: Upload Page Shows Task Details

```
📤 Upload PDF Page (with task details)
┌─────────────────────────────────────────────────────┐
│              📊 Current Task Status                 │
├─────────────────────────────────────────────────────┤
│ Task ID: 10 │ Status: ✅ COMPLETED │ Progress: 100%│
│             │ File: report.pdf                      │
├─────────────────────────────────────────────────────┤
│ ✅ Processing completed!                            │
│                                                     │
│ [📥 View Results] ← Click to see extracted content │
├─────────────────────────────────────────────────────┤
│ ⏰ Timeline                                         │
│ Created: 2026-02-17 10:30:15                       │
│ Started: 2026-02-17 10:30:18                       │
│ Completed: 2026-02-17 10:30:25                     │
├─────────────────────────────────────────────────────┤
│ [🔄 Refresh Status] │ [🗑️ Delete Task]             │
└─────────────────────────────────────────────────────┘
```

### After Clicking "View Results": Full Extraction Results

```
📥 Extraction Results
┌─────────────────────────────────────────────────────┐
│ Pages: 5 │ Characters: 15,234 │ Tables: 3 │ Time: 12.4s│
├─────────────────────────────────────────────────────┤
│ [📝 Text] [📊 Tables] [🖼️ Images] [📋 Metadata]   │
├─────────────────────────────────────────────────────┤
│                                                     │
│ ← Currently showing the "Text" tab                 │
│                                                     │
│ ┌─────────────────────────────────────────────┐   │
│ │ Full extracted text content...               │   │
│ │ [Scrollable area]                            │   │
│ │ Lorem ipsum dolor sit amet...                │   │
│ └─────────────────────────────────────────────┘   │
│                                                     │
│ [💾 Download Text]                                 │
└─────────────────────────────────────────────────────┘
```

---

## 🎯 Different States & What They Show

### 1. PENDING Task (Just Uploaded)

```
📊 Task Status
Task ID: 10 │ Status: 🟡 PENDING │ Progress: 0%
File: document.pdf

⏳ Task is pending... Waiting for worker to pick it up from SQS queue.

⏰ Timeline
Created: 2026-02-17 10:30:15
Started: (not yet)
Completed: (not yet)

[🔄 Refresh Status] │ [🗑️ Delete Task]
```

**No "View Results" button** - task hasn't been processed yet

---

### 2. PROCESSING Task (In Progress)

```
📊 Task Status
Task ID: 10 │ Status: 🔵 PROCESSING │ Progress: 60%
File: document.pdf

[████████████████░░░░░░░░ 60%]

📊 Extracting tables... Identifying and structuring table data.

⏰ Timeline
Created: 2026-02-17 10:30:15
Started: 2026-02-17 10:30:18
Completed: (in progress)

[🔄 Refresh Status] │ [🗑️ Delete Task]
```

**No "View Results" button** - results not ready yet  
**Shows live progress** with detailed step messages

---

### 3. COMPLETED Task (Success!)

```
📊 Task Status
Task ID: 10 │ Status: ✅ COMPLETED │ Progress: 100%
File: document.pdf

✅ Processing completed!

[📥 View Results] ← Click to see full extraction

⏰ Timeline
Created: 2026-02-17 10:30:15
Started: 2026-02-17 10:30:18
Completed: 2026-02-17 10:30:25 (7 seconds)

[🔄 Refresh Status] │ [🗑️ Delete Task]
```

**"View Results" button appears** - click to see:
- Full extracted text
- Tables as DataFrames
- Image metadata
- Document properties

---

### 4. FAILED Task (Error)

```
📊 Task Status
Task ID: 10 │ Status: 🔴 FAILED │ Progress: 40%
File: document.pdf

❌ Processing failed: LlamaParse API timeout - please retry

⏰ Timeline
Created: 2026-02-17 10:30:15
Started: 2026-02-17 10:30:18
Completed: (failed at 10:30:22)

[🔄 Refresh Status] │ [🗑️ Delete Task]
```

**No "View Results" button** - task failed  
**Shows error message** explaining what went wrong

---

## 💡 Key Features of the View Display

### ✅ Real-Time Updates
- If auto-refresh is enabled, status updates every 1 second
- Progress bar animates smoothly
- Status messages change based on progress

### ✅ Comprehensive Information
- Task metadata (ID, status, progress, filename)
- Timeline (created, started, completed)
- Full extraction results (text, tables, images, metadata)

### ✅ Interactive Elements
- **Download button** for extracted text
- **Sortable/searchable DataFrames** for tables
- **Expandable timeline** to save space
- **Refresh button** to manually update
- **Delete button** to remove task

### ✅ Smart Display
- Only shows "View Results" when task is completed
- Shows progress bar only for active tasks
- Shows error message only for failed tasks
- Adapts to different task states automatically

---

## 📊 Data Sources

The View button fetches data from:

1. **Redis** (fast, real-time):
   - Task status
   - Progress percentage
   - Timestamps
   - Metadata

2. **PostgreSQL** (fallback, permanent):
   - If Redis data expired
   - Document record
   - Result text
   - Status history

3. **Backend API Endpoints**:
   - `/status/{task_id}` - Get current status
   - `/result/{task_id}` - Get extraction results

---

## 🎯 Summary

**When you click "View" on a task:**

1. **Navigate** to Upload page
2. **Show** task status card with metrics
3. **Display** progress bar (if active) or success/error message
4. **Show** timeline with timestamps
5. **Offer** "View Results" button (if completed)
6. **When "View Results" clicked**, show:
   - Summary metrics
   - 4 tabs: Text, Tables, Images, Metadata
   - Download button for text
   - Interactive data displays

**The View button gives you a complete, detailed view of the task's journey from upload to completion!** 🚀

---

*Documentation Version: 1.3.0*  
*Last Updated: February 17, 2026*
