// Simple health endpoint for Vercel demo backend
module.exports = (req, res) => {
  res.setHeader('Content-Type', 'application/json');
  res.status(200).json({ status: 'healthy', backend: 'demo', message: 'Demo backend on Vercel is running.' });
};
