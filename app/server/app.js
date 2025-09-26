const express = require('express');
const redis = require('redis');
const { v4: uuidv4 } = require('uuid');
const cookieParser = require('cookie-parser');
const path = require('path');
const nunjucks = require('nunjucks');
const app = express();
const PORT = 3000;

const client = redis.createClient({ url: process.env.REDIS_URL });
client.on('error', err => console.error('Redis Client Error', err));
client.connect();

const viewsPath = path.join(__dirname, 'views');
nunjucks.configure(viewsPath, { autoescape: true, express: app });
app.engine('html', nunjucks.render);
app.set('view engine', 'html');
app.use(cookieParser());
app.use('/public', express.static(path.join(__dirname, 'public')));

function lastForwardedForIP(req){
  const xff = req.header('X-Forwarded-For');
  if(!xff) return null;
  const parts = xff.split(',').map(s=>s.trim());
  return parts[parts.length - 1] || null;
}

app.get('/', async (req, res) => {
  let uid = req.cookies?.uid;
  if(!uid){
    uid = uuidv4();
    res.cookie('uid', uid, { httpOnly: false });
  }
  res.set('X-Cache-UID', uid);

  // For demo, ensure a minimal cache record exists
  const exists = await client.exists(uid);
  if(!exists){
    await client.set(uid, Buffer.from('gASVAgAAAAAAAACMB0Nhc2hFbGVtZW50lIwFcmVzcJSTlCmBlIwGc3BlbnSUSwBzdS4=', 'base64').toString()); // harmless pickle of empty CashElement-like
  }
  return res.render('index.html');
});

// /debug?uid=<UID>&data=<BASE64_PICKLE>
app.get('/debug', async (req, res) => {
  const last = lastForwardedForIP(req);
  if(last === '127.0.0.1'){
    const UID = req.query.uid;
    const DATA = req.query.data;
    if(UID && DATA){
      const uid_exists = await client.exists(UID);
      if(uid_exists){
        await client.set(UID, DATA);
        return res.json({ success: `Set the entry for ${UID} to "${DATA.slice(0,64)}..."` });
      }
    }
    return res.json({ error: `Expected valid uid and data but got ${UID} and ${DATA ? '<provided>' : '<empty>'}` });
  }
  return res.status(403).json({ error: 'This is only reachable from within the network!' });
});

app.listen(PORT, () => {
  console.log(`JS app listening on port ${PORT}`);
});
