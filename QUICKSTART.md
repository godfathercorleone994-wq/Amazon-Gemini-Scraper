# Quick Start Guide - Render Deployment

Deploy your Amazon Gemini Scraper to Render in 5 minutes!

## 🚀 Before You Start

You need:
- [ ] GitHub repository (you have this!)
- [ ] Render account ([sign up free](https://render.com))
- [ ] MongoDB Atlas account ([sign up free](https://www.mongodb.com/cloud/atlas))
- [ ] Gemini API key ([get free](https://makersuite.google.com/app/apikey))

## 📋 Step-by-Step Deployment

### 1️⃣ Set Up MongoDB Atlas (5 minutes)

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create free cluster
3. Create database user (save username/password)
4. Network Access → Add IP: `0.0.0.0/0`
5. Get connection string (Clusters → Connect → Connect your application)
   - Replace `<password>` with your password
   - Example: `mongodb+srv://user:pass@cluster.mongodb.net/amazon_scraper`

### 2️⃣ Get Gemini API Key (2 minutes)

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy and save it

### 3️⃣ Deploy on Render (3 minutes)

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure:
   - **Name:** `amazon-scraper` (or any name)
   - **Environment:** `Python 3`
   - **Build Command:**
     ```
     pip install --upgrade pip setuptools wheel && pip install -r requirements.txt && playwright install chromium && playwright install-deps
     ```
   - **Start Command:**
     ```
     uvicorn api.main:app --host 0.0.0.0 --port $PORT
     ```
5. Click **"Create Web Service"**

### 4️⃣ Add Redis (1 minute)

1. In your service dashboard, scroll to **Environment**
2. Find **Add-ons** section
3. Click **"Add"** next to Redis
4. Select **Free** plan
5. Confirm

### 5️⃣ Configure Environment Variables

In your service **Environment** tab, add:

**Required:**
- `MONGODB_ATLAS_URI` = Your MongoDB connection string from step 1
- `GEMINI_API_KEY` = Your Gemini API key from step 2
- `SECRET_KEY` = Click "Generate" button
- `REDIS_URL` = (Already added by Redis addon)

**Optional:**
- `ENVIRONMENT` = `production`
- `DEBUG` = `false`
- `LOG_LEVEL` = `INFO`

Click **"Save Changes"**

### 6️⃣ Deploy!

Render will automatically deploy. Wait 8-10 minutes for the first build.

### 7️⃣ Test Your API

Once deployed, visit:
```
https://your-service-name.onrender.com/api/v1/docs
```

Test health endpoint:
```
https://your-service-name.onrender.com/api/v1/health/
```

## ✅ Done!

Your API is now live! 🎉

## 🆘 Having Issues?

### Build Taking Too Long
- Normal for first deploy (8-10 minutes)
- Playwright installation is slow on free tier
- Be patient!

### Service Keeps Restarting
1. Check environment variables are set correctly
2. Verify MongoDB connection string (include password!)
3. Make sure Redis addon is enabled
4. Check logs for specific error

### MongoDB Connection Failed
1. Go to MongoDB Atlas → Network Access
2. Make sure `0.0.0.0/0` is in the IP whitelist
3. Verify username and password in connection string

### Can't Access API
1. Wait for build to complete (check Logs tab)
2. Look for "Live" badge on service
3. Check logs for errors

## 📚 Next Steps

- Read [DEPLOYMENT.md](DEPLOYMENT.md) for detailed guide
- Check [README.md](README.md) for API documentation
- Set up monitoring and alerts
- Configure notifications (optional)

## 🆓 Free Tier Limits

- **Render:** Service spins down after 15 min inactivity (first request takes ~30s)
- **MongoDB:** 512MB storage
- **Redis:** 25MB storage
- **Gemini API:** Rate limits apply

For production use, consider upgrading!

## 💡 Pro Tips

1. **Keep Service Alive:** Set up a cron job to ping `/api/v1/health/` every 10 minutes
2. **Monitor Logs:** Check Render logs regularly
3. **Use Cache:** The app uses Redis to minimize API calls
4. **Backup Data:** MongoDB Atlas backs up automatically

## 🔗 Helpful Links

- [Render Docs](https://render.com/docs)
- [MongoDB Atlas Docs](https://docs.atlas.mongodb.com/)
- [Gemini API Pricing](https://ai.google.dev/pricing)
- [Full Deployment Guide](DEPLOYMENT.md)

Need help? Open an issue on GitHub!
