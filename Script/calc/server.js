const http = require('http');
const fs = require('fs');
const path = require('path');

http.createServer((req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate'); // Sem cache!

    const filePath = path.join(__dirname, req.url.split('?')[0]);
    if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
        res.writeHead(200, { 'Content-Type': 'application/javascript' });
        res.end(fs.readFileSync(filePath));
    } else {
        res.writeHead(404);
        res.end('Not found');
    }
}).listen(8123, () => {
    console.log('Servidor local rodando em http://127.0.0.1:8123/');
});
