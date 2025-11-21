import sys
import socket
import threading
import json
import urllib.request
import urllib.error
import time

# Cấu hình Proxy Server (Nơi gửi API request)
SERVER_URL = "http://127.0.0.1:8080"

class PeerClient:
    def __init__(self, username, port):
        self.username = username
        self.my_ip = "127.0.0.1"
        self.my_port = int(port)
        self.peers = [] # Danh sách peer lấy từ server
        self.running = True

    # -------------------------------------------------------
    # PHẦN 1: P2P LISTENER (Nhận tin nhắn từ Peer khác)
    # -------------------------------------------------------
    def start_listening(self):
        """Mở socket TCP để nhận kết nối từ các Peer khác"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server_socket.bind((self.my_ip, self.my_port))
            server_socket.listen(5)
            print(f"\n[P2P] {self.username} đang lắng nghe tin nhắn tại {self.my_ip}:{self.my_port}")
            
            while self.running:
                client_sock, addr = server_socket.accept()
                # Tạo thread xử lý tin nhắn đến để không chặn luồng chính
                threading.Thread(target=self.handle_incoming_message, args=(client_sock,)).start()
        except Exception as e:
            print(f"[Error] Không thể bind port {self.my_port}. Có thể port đang bận.")
            self.running = False
        finally:
            server_socket.close()

    def handle_incoming_message(self, conn):
        """Xử lý tin nhắn nhận được"""
        try:
            data = conn.recv(1024).decode('utf-8')
            if data:
                # Giả sử tin nhắn format dạng: "SENDER_NAME|MESSAGE"
                if "|" in data:
                    sender, msg = data.split("|", 1)
                    print(f"\n>>> 📩 Tin nhắn từ [{sender}]: {msg}")
                    print(">>> Nhập lệnh: ", end="", flush=True)
                else:
                    print(f"\n>>> 📩 Tin nhắn lạ: {data}")
        except Exception as e:
            print(f"[Error Reading] {e}")
        finally:
            conn.close()

    # -------------------------------------------------------
    # PHẦN 2: CLIENT API (Giao tiếp với Server trung tâm)
    # -------------------------------------------------------
    def call_api(self, endpoint, method="POST", data=None):
        url = f"{SERVER_URL}{endpoint}"
        req = urllib.request.Request(url, method=method)
        req.add_header('Content-Type', 'application/json')
        
        try:
            body = json.dumps(data).encode('utf-8') if data else None
            with urllib.request.urlopen(req, data=body) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            print(f"[API Error] {e.code} - {e.reason}")
            return None
        except Exception as e:
            print(f"[Network Error] {e}")
            return None

    def register(self):
        print(f"[*] Đang đăng ký {self.username} lên Server...")
        payload = {
            "username": self.username,
            "ip": self.my_ip,
            "port": self.my_port
        }
        res = self.call_api("/submit-info", data=payload)
        if res and res.get("status") == "ok":
            print("[Success] Đăng ký thành công!")
        else:
            print("[Fail] Đăng ký thất bại.")

    def update_peer_list(self):
        res = self.call_api("/get-list", method="GET")
        if res and res.get("status") == "ok":
            self.peers = res.get("active_peers", [])
            print(f"\n[*] Danh sách Online ({len(self.peers)}):")
            for p in self.peers:
                if p['username'] != self.username:
                    print(f" - {p['username']} ({p['ip']}:{p['port']})")
        else:
            print("[!] Không lấy được danh sách peer.")

    # -------------------------------------------------------
    # PHẦN 3: GỬI TIN NHẮN (Connect tới Peer khác)
    # -------------------------------------------------------
    def send_direct(self, target_name, message):
        # Tìm target trong danh sách
        target = next((p for p in self.peers if p['username'] == target_name), None)
        
        if not target:
            print(f"[!] Không tìm thấy user '{target_name}'. Hãy cập nhật danh sách (chọn 1).")
            return

        try:
            # Kết nối trực tiếp TCP tới Peer
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((target['ip'], target['port']))
            
            # Gửi format: TÊN_MÌNH|NỘI_DUNG
            full_msg = f"{self.username}|{message}"
            s.sendall(full_msg.encode('utf-8'))
            s.close()
            print(f"[Sent] Đã gửi tới {target_name}")
        except Exception as e:
            print(f"[Error] Không thể kết nối tới {target_name} ({target['ip']}:{target['port']}): {e}")

    # Tìm đến hàm broadcast cũ và thay thế bằng đoạn code này
    def broadcast(self, message):
        # BƯỚC 1: Tự động cập nhật danh sách mới nhất từ Server
        # Để đảm bảo không bỏ sót người mới vào (như người thứ 3, 4)
        print("[Sync] Đang đồng bộ danh sách mới nhất...")
        self.update_peer_list()

        # BƯỚC 2: Tiến hành gửi
        print("[*] Đang gửi Broadcast...")
        count = 0
        for p in self.peers:
            # Không gửi cho chính mình
            if p['username'] != self.username:
                self.send_direct(p['username'], message)
                count += 1
        
        if count == 0:
            print("[Info] Không có ai khác để gửi (Bạn đang online một mình).")
        else:
            print(f"[Done] Đã gửi tin nhắn cho {count} người.")

    # -------------------------------------------------------
    # VÒNG LẶP CHÍNH (UI)
    # -------------------------------------------------------
    def run(self):
        # 1. Khởi động thread lắng nghe
        t = threading.Thread(target=self.start_listening)
        t.daemon = True
        t.start()

        # 2. Đăng ký với server
        time.sleep(1) # Đợi listener ổn định
        self.register()

        # 3. Menu điều khiển
        print("\n========= CHAT P2P TERMINAL =========")
        print("1. Cập nhật danh sách Peer (Get List)")
        print("2. Gửi tin nhắn riêng (Direct P2P)")
        print("3. Gửi tin nhắn cho tất cả (Broadcast P2P)")
        print("4. Đăng ký lại (nếu Server restart)")
        print("0. Thoát")
        print("=====================================")

        while self.running:
            try:
                choice = input("\n>>> Nhập lệnh (0-4): ").strip()
                
                if choice == '1':
                    self.update_peer_list()
                
                elif choice == '2':
                    target = input("Nhập tên người nhận: ")
                    msg = input("Nội dung tin nhắn: ")
                    self.send_direct(target, msg)
                
                elif choice == '3':
                    if not self.peers:
                        self.update_peer_list()
                    msg = input("Nội dung Broadcast: ")
                    self.broadcast(msg)
                
                elif choice == '4':
                    self.register()

                elif choice == '0':
                    print("Tạm biệt!")
                    self.running = False
                    sys.exit(0)
                
            except KeyboardInterrupt:
                print("\nThoát.")
                sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Cách dùng: python peer_client.py [USERNAME] [PORT]")
        print("Ví dụ:     python peer_client.py Alice 9001")
        sys.exit(1)

    u_name = sys.argv[1]
    u_port = sys.argv[2]
    
    client = PeerClient(u_name, u_port)
    client.run()
