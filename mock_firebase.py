import json
import time
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# Global state for the mock trades
current_trade = {}

def generate_random_trade():
    """Continuously generates a random trade every 5 seconds."""
    global current_trade
    symbols = ["NIFTY 24MAY 22000 CE", "BANKNIFTY 24MAY 48000 PE", "RELIANCE EQ", "INFY EQ"]
    statuses = ["BUY", "SELL", "TARGET REACHED", "SL HIT"]
    
    while True:
        current_trade = {
            "symbol": random.choice(symbols),
            "entry": round(random.uniform(10.0, 500.0), 2),
            "sl": round(random.uniform(5.0, 490.0), 2),
            "status": random.choice(statuses),
            "timestamp": int(time.time() * 1000)  # JS style timestamp in ms
        }
        print(f"[{time.strftime('%H:%M:%S')}] Generated new trade: {current_trade['status']} {current_trade['symbol']}")
        time.sleep(5)

class MockFirebaseHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # We simulate Firebase by responding to any .json endpoint
        if self.path.endswith('.json'):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response_json = json.dumps(current_trade)
            self.wfile.write(response_json.encode('utf-8'))
        else:
            # Simulate Firebase HTML response if user forgets .json
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<html><body>This is a Firebase database interface. Append .json to get data.</body></html>")

    def log_message(self, format, *args):
        # Suppress noisy HTTP request logging
        pass

if __name__ == "__main__":
    print("=====================================================")
    print("Starting Mock Firebase Server on port 5000")
    print("Point your Flet app to: http://localhost:5000/.json")
    print("=====================================================")
    
    # Start the trade generator in a background thread
    threading.Thread(target=generate_random_trade, daemon=True).start()
    
    # Start the HTTP server
    server_address = ('127.0.0.1', 5000)
    httpd = HTTPServer(server_address, MockFirebaseHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
