# Production Troubleshooting Guide

## Common Production Errors

### 1. 500 Internal Server Error on `/aria/init`

**Symptom:** Frontend shows "Error 500" when clicking Initialize button

**Root Cause:** Missing `OPENAI_API_KEY` environment variable in production

**Solution:**

#### For Render/Railway/Fly:
1. Go to your backend service dashboard
2. Navigate to Environment Variables
3. Add: `OPENAI_API_KEY=sk-proj-...` (your actual key)
4. Redeploy the service

#### For Vercel (if deploying backend there - NOT recommended):
```bash
vercel env add OPENAI_API_KEY
# Enter your key when prompted
# Select Production environment
vercel --prod
```

#### Verify Fix:
```bash
curl https://your-backend-url.com/aria/health
```

Expected response:
```json
{
  "status": "healthy",
  "openai_configured": true,
  "openai_key_length": 164,
  "initialized": false
}
```

If `openai_configured: false`, the API key is still missing.

---

### 2. 404 Not Found on `/aria/strategy`

**Symptom:** Frontend shows 404 when trying to fetch strategy

**Root Cause:** ARIA not initialized after backend restart

**Solution:**

Backend state is in-memory and lost on restart. You must re-initialize:

```bash
curl -X POST https://your-backend-url.com/aria/init \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://yourbrand.com",
    "goal": "purchases",
    "budget_daily": 1000,
    "business_type": "B2C",
    "brand_name": "Your Brand"
  }'
```

Or use the frontend Initialize button.

---

### 3. CORS Errors

**Symptom:** Browser console shows CORS policy errors

**Root Cause:** Frontend domain not allowed by backend CORS settings

**Solution:**

Update `backend/app/main.py` CORS configuration:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://your-frontend.vercel.app"  # Add your production domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Redeploy backend after changes.

---

### 4. WebSocket Connection Failed

**Symptom:** Live feed not updating, console shows WebSocket errors

**Root Cause:** WebSocket protocol mismatch or firewall blocking

**Solution:**

Ensure frontend uses correct WebSocket URL:
- Local: `ws://127.0.0.1:8000/aria/live`
- Production HTTPS: `wss://your-backend.com/aria/live` (note: `wss://` not `ws://`)

Update `frontend/src/api.js`:
```javascript
const wsBase = apiBase.replace("https", "wss").replace("http", "ws");
```

---

### 5. Frontend Shows "VITE_API_BASE is undefined"

**Symptom:** API calls fail with connection errors

**Root Cause:** Missing environment variable in Vercel

**Solution:**

1. Go to Vercel project settings
2. Environment Variables tab
3. Add: `VITE_API_BASE=https://your-backend-url.com`
4. Redeploy frontend

---

## Health Check Endpoints

### Backend Health
```bash
curl https://your-backend-url.com/aria/health
```

Returns:
- `status`: "healthy"
- `openai_configured`: true/false
- `openai_key_length`: number (should be ~164 for valid key)
- `initialized`: true/false (ARIA state exists)

### Backend API Docs
```bash
open https://your-backend-url.com/docs
```

Interactive Swagger UI for testing endpoints.

---

## Deployment Checklist

### Backend (Render/Railway/Fly)

- [ ] Repository connected
- [ ] Environment variable `OPENAI_API_KEY` set
- [ ] Build command: `pip install -r backend/requirements.txt`
- [ ] Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --app-dir backend`
- [ ] Health check path: `/aria/health`
- [ ] Service deployed and running

### Frontend (Vercel)

- [ ] Repository imported
- [ ] Environment variable `VITE_API_BASE` set to backend URL
- [ ] Build command: `npm run build --prefix frontend`
- [ ] Output directory: `frontend/dist`
- [ ] Deployment successful

### Post-Deployment

- [ ] Visit frontend URL
- [ ] Check browser console for errors
- [ ] Click Initialize button
- [ ] Verify strategy data loads
- [ ] Test Platform Comparison page
- [ ] Verify live feed updates

---

## Getting Strategy Data

After initialization, the `/aria/strategy` endpoint returns:

```json
{
  "production_information": {
    "product_name": "AI-Powered Advertising Solutions",
    "product_category": "Digital Marketing",
    "offer_summary": "Leverage cutting-edge AI technology...",
    "price_point": "$299/month",
    "brand_url": "https://adsgency.ai/"
  },
  "platform": {
    "channels": ["webads", "images", "videos"],
    "images_required": 5,
    "videos_required": 2
  },
  "target_audience": {
    "primary_segment": "Small to Medium Enterprises (SMEs)",
    "age_range": "25-45",
    "geography": ["United States", "Canada", "United Kingdom"],
    "interests": ["digital marketing", "business growth", "technology"],
    "belief_state": "Seeking effective advertising solutions...",
    "key_objections": ["Budget constraints", "Skepticism about AI effectiveness"]
  },
  "generations": {
    "copies_per_cycle": 3,
    "max_generations": 5,
    "active_generation": 2
  },
  "performance_history": {
    "platform_user_click_history": [
      {
        "platform": "meta",
        "user_clicks": 1500,
        "integrations_from_sites": ["Facebook", "Instagram"],
        "paid_conversions": 150,
        "conversion_rate": 0.1
      },
      {
        "platform": "google",
        "user_clicks": 1200,
        "integrations_from_sites": ["Google Ads"],
        "paid_conversions": 120,
        "conversion_rate": 0.1
      }
    ],
    "overall_conversion_rate": 0.1
  }
}
```

### Fetching Strategy Data

**Via curl:**
```bash
curl https://your-backend-url.com/aria/strategy
```

**Via frontend:**
```javascript
const response = await fetch(`${apiBase}/aria/strategy`);
const strategy = await response.json();
console.log(strategy);
```

**Important:** Must call `POST /aria/init` first, or you'll get 404.

---

## Logs and Debugging

### View Backend Logs (Render)
```bash
# In Render dashboard
Services → Your Service → Logs
```

### View Backend Logs (Railway)
```bash
railway logs
```

### View Backend Logs (Fly)
```bash
fly logs
```

### Common Log Errors

**"OPENAI_API_KEY environment variable is not set"**
→ Add the environment variable in your hosting dashboard

**"OpenAI initialization payload was not valid JSON"**
→ OpenAI returned non-JSON response, check API quota/limits

**"ModuleNotFoundError: No module named 'langgraph'"**
→ Dependencies not installed, check build command

**"Address already in use"**
→ Port conflict, ensure `--port $PORT` in start command

---

## Performance Optimization

### Backend
- Use production ASGI server (Uvicorn with workers)
- Enable HTTP/2 if supported by host
- Add Redis for event caching (future enhancement)

### Frontend
- Vercel automatically optimizes builds
- Enable Vercel Analytics for monitoring
- Use CDN for static assets

---

## Security Best Practices

1. **Never commit API keys** - Use environment variables only
2. **Rotate keys regularly** - Update `OPENAI_API_KEY` monthly
3. **Restrict CORS** - Only allow your frontend domain
4. **Use HTTPS** - Always use SSL in production
5. **Rate limiting** - Consider adding rate limits to prevent abuse

---

## Support

If issues persist:

1. Check `/aria/health` endpoint
2. Review backend logs
3. Verify environment variables
4. Test with curl before frontend
5. Check browser console for client-side errors

For OpenAI API issues:
- Check quota: https://platform.openai.com/usage
- Verify API key: https://platform.openai.com/api-keys
- Review rate limits: https://platform.openai.com/docs/guides/rate-limits
