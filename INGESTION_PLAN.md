# Batch Ingestion Plan

## Problem
- Full ingestion of 171 documents fails due to token limit errors
- Some large documents (rec.autos with 918 chunks) cause issues
- Need to ingest in smaller batches

## Solution: Batch Ingestion

### Step 1: Check Current Status
```powershell
python batch_ingest.py status
```

This shows:
- Total documents
- How many are ingested
- Which ones are missing

### Step 2: Ingest in Batches of 50

**Batch 1 (Documents 0-49):**
```powershell
python batch_ingest.py batch 0 50
```

**Batch 2 (Documents 50-99):**
```powershell
python batch_ingest.py batch 50 50
```

**Batch 3 (Documents 100-149):**
```powershell
python batch_ingest.py batch 100 50
```

**Batch 4 (Documents 150-171):**
```powershell
python batch_ingest.py batch 150 25
```

### Step 3: Verify After Each Batch
```powershell
python batch_ingest.py status
```

### Step 4: Once All Complete
```powershell
# Commit and push
git add data/ logs/
git commit -m "Add pre-ingested storage: all 171 documents"
git push origin main
```

## Benefits of Batch Approach

✅ **Sequential processing** - One document at a time, no parallel issues
✅ **Smaller memory footprint** - Processes 50 docs then saves
✅ **Resume capability** - Can stop and restart anytime
✅ **Progress tracking** - See exactly which docs are done
✅ **Error isolation** - One bad doc doesn't kill entire batch

## If a Batch Fails

1. Check status to see what was ingested:
   ```powershell
   python batch_ingest.py status
   ```

2. Re-run the same batch:
   ```powershell
   python batch_ingest.py batch <start> 50
   ```

3. The script will skip already-ingested docs automatically

## Storage Locations

After ingestion, these folders will have data:
- `data/chroma_db/` - Vector embeddings
- `data/whoosh_index/` - Keyword index  
- `data/knowledge_graph/` - Graph data
- `logs/ingestion_registry.jsonl` - Registry
- `logs/audit_logs.jsonl` - Audit logs

## Final Step: Deploy to Render

Once all 171 documents are ingested locally:

1. Commit storage files:
   ```powershell
   git add -A
   git commit -m "Add complete pre-ingested storage (171 docs)"
   git push origin main
   ```

2. Render auto-deploys with all data!

3. Verify on Render:
   ```
   https://complete-enterprise-assistant.onrender.com/frontend/dashboard.html
   ```

Should show all 171 documents ready to query!
