import customtkinter as ctk
import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import cv2
import numpy as np
import pytesseract
import os
import time
import winsound
import datetime

# --- 設定區 ---
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

class TicketBotApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TixCraft 拓元搶票機器人 (戰術延遲版)")
        self.geometry("650x850") 
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.driver = None
        self.is_running = False
        self.create_widgets()

    def create_widgets(self):
        self.label_title = ctk.CTkLabel(self, text="🎫 拓元自動搶票系統", font=("Microsoft JhengHei UI", 24, "bold"))
        self.label_title.pack(pady=15)

        # 區域 1: 帳號
        self.login_frame = ctk.CTkFrame(self)
        self.login_frame.pack(pady=5, padx=20, fill="x")
        ctk.CTkLabel(self.login_frame, text="【FB 自動登入設定】", font=("Microsoft JhengHei UI", 14, "bold")).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(self.login_frame, text="FB 帳號:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.fb_user_entry = ctk.CTkEntry(self.login_frame, width=250); self.fb_user_entry.grid(row=1, column=1, padx=10, pady=5)
        ctk.CTkLabel(self.login_frame, text="FB 密碼:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.fb_pwd_entry = ctk.CTkEntry(self.login_frame, width=250, show="*"); self.fb_pwd_entry.grid(row=2, column=1, padx=10, pady=5)

        # 區域 2: 時間
        self.time_frame = ctk.CTkFrame(self)
        self.time_frame.pack(pady=5, padx=20, fill="x")
        ctk.CTkLabel(self.time_frame, text="【定時開搶設定】", font=("Microsoft JhengHei UI", 14, "bold")).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.schedule_var = ctk.StringVar(value="off")
        self.schedule_switch = ctk.CTkSwitch(self.time_frame, text="啟用定時開搶", variable=self.schedule_var, onvalue="on", offvalue="off")
        self.schedule_switch.grid(row=0, column=1, padx=10, pady=5, sticky="e")
        ctk.CTkLabel(self.time_frame, text="開賣時間:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.time_entry = ctk.CTkEntry(self.time_frame, width=150); self.time_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        self.time_entry.insert(0, (datetime.datetime.now() + datetime.timedelta(hours=1)).replace(minute=0, second=0).strftime("%H:%M:%S"))

        # 區域 3: 參數
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(pady=5, padx=20, fill="x")
        ctk.CTkLabel(self.input_frame, text="活動網址:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.url_entry = ctk.CTkEntry(self.input_frame, width=350); self.url_entry.grid(row=1, column=1, padx=10, pady=5)
        self.url_entry.insert(0, "https://tixcraft.com/activity/detail/26_treasure")
        ctk.CTkLabel(self.input_frame, text="目標價格:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.price_entry = ctk.CTkEntry(self.input_frame, width=350); self.price_entry.grid(row=2, column=1, padx=10, pady=5); self.price_entry.insert(0, "5800")
        ctk.CTkLabel(self.input_frame, text="購買張數:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.ticket_num_combo = ctk.CTkComboBox(self.input_frame, values=["1", "2", "3", "4"], width=100); self.ticket_num_combo.grid(row=3, column=1, padx=10, pady=5, sticky="w"); self.ticket_num_combo.set("1")
        self.fallback_var = ctk.StringVar(value="on")
        ctk.CTkSwitch(self.input_frame, text="啟用備案", variable=self.fallback_var, onvalue="on", offvalue="off").grid(row=4, column=0, columnspan=2)

        # 按鈕與 Log
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent"); self.btn_frame.pack(pady=10)
        self.start_btn = ctk.CTkButton(self.btn_frame, text="啟動機器人", command=self.start_bot_thread, width=180, height=50, fg_color="#2CC985"); self.start_btn.pack(side="left", padx=10)
        self.stop_btn = ctk.CTkButton(self.btn_frame, text="停止", command=self.stop_bot, width=100, height=50, fg_color="#C92C2C"); self.stop_btn.pack(side="left", padx=10)
        
        self.log_label = ctk.CTkLabel(self, text="執行紀錄:", font=("Microsoft JhengHei UI", 14)); self.log_label.pack(pady=(5, 0), padx=20, anchor="w")
        self.log_box = ctk.CTkTextbox(self, width=600, height=180, font=("Consolas", 12)); self.log_box.pack(pady=5, padx=20)
        self.log("系統就緒。")

    def log(self, message):
        timestamp = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3] # 顯示到毫秒
        self.log_box.insert("end", f"[{timestamp}] {message}\n")
        self.log_box.see("end")
        print(f"[{timestamp}] {message}")

    def start_bot_thread(self):
        if self.is_running: return
        self.is_running = True
        self.start_btn.configure(state="disabled", text="執行中...")
        threading.Thread(target=self.run_scheduler_logic, daemon=True).start()

    def stop_bot(self):
        self.is_running = False
        if self.driver:
            try: self.driver.quit()
            except: pass
        self.log("已手動停止程式。")
        self.start_btn.configure(state="normal", text="啟動機器人")

    # ================= 核心邏輯區 =================

    def init_driver(self):
        self.log("初始化 Chrome...")
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def run_scheduler_logic(self):
        try:
            target_url = self.url_entry.get()
            if self.schedule_var.get() == "on":
                target_time_str = self.time_entry.get()
                now = datetime.datetime.now()
                target_time = datetime.datetime.strptime(target_time_str, "%H:%M:%S").replace(year=now.year, month=now.month, day=now.day)
                
                # 自動判斷跨日
                if target_time < now:
                    target_time += datetime.timedelta(days=1)
                    self.log(f"提示：時間已過，判定為搶「明天」的票。")

                minutes_ahead = 2
                launch_time = target_time - datetime.timedelta(minutes=minutes_ahead)
                
                # 如果啟動時間已過，立即啟動
                if launch_time < datetime.datetime.now():
                    self.log("啟動時間已過，立即啟動瀏覽器！")
                else:
                    self.log(f"定時模式：預計 {launch_time.strftime('%H:%M:%S')} 啟動")
                    while datetime.datetime.now() < launch_time and self.is_running:
                        time.sleep(1)
                    if not self.is_running: return

                self.log(">>> 啟動瀏覽器 <<<")
                self.init_driver()
                
                # 雙重登入確保
                self.perform_fb_login()
                time.sleep(2)
                self.perform_fb_login() 

                self.log(f"前往活動頁: {target_url}")
                self.driver.get(target_url)
                
                self.log(f"等待 {target_time.strftime('%H:%M:%S')} 開賣...")
                
                # 精確等待直到開賣時間
                while datetime.datetime.now() < target_time and self.is_running:
                    time.sleep(0.01) # 縮短檢查間隔以提高精度
                
                # ==========================================
                # 【戰術延遲】 避免刷新太快讀到舊快取
                # ==========================================
                refresh_delay = 0.2  # 單位：秒 (建議 0.1 ~ 0.5)
                self.log(f">>> 時間到！戰術延遲 {refresh_delay}秒 <<<")
                time.sleep(refresh_delay)
                
                self.log(">>> 執行刷新！ <<<")
                self.driver.refresh() 
            else:
                self.log("立即模式...")
                self.init_driver()
                self.perform_fb_login()
                time.sleep(2)
                self.perform_fb_login()
                self.log(f"前往活動頁: {target_url}")
                self.driver.get(target_url)

            self.run_ticket_process()

        except Exception as e:
            self.log(f"錯誤: {e}")
        finally:
            if not self.driver: 
                self.start_btn.configure(state="normal", text="啟動機器人")
                self.is_running = False

    def perform_fb_login(self):
        """ FB 登入邏輯：死守輸入框 """
        fb_user = self.fb_user_entry.get()
        fb_pwd = self.fb_pwd_entry.get()

        if not fb_user or not fb_pwd:
            self.log("未輸入 FB 帳密，跳過。")
            return

        self.log("前往首頁登入...")
        self.driver.get("https://tixcraft.com/")
        wait = WebDriverWait(self.driver, 10)

        try:
            try:
                login_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@href='#login']")))
                login_btn.click()
            except:
                self.log("已是登入狀態，跳過。")
                return

            self.log("點擊 Facebook 登入...")
            fb_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//img[contains(@src, 'facebook')]")))
            fb_btn.click()

            self.log("等待 FB 頁面...")
            time.sleep(3)

            try:
                email_input = wait.until(EC.presence_of_element_located((By.ID, "email")))
                self.log("輸入帳密...")
                email_input.clear(); email_input.send_keys(fb_user)
                pass_input = self.driver.find_element(By.ID, "pass")
                pass_input.clear(); pass_input.send_keys(fb_pwd)
                self.driver.find_element(By.Name, "login").click()
                self.log("送出帳密...")
            except:
                self.log("未找到輸入框 (可能已登入)，繼續...")

            for i in range(60):
                if "tixcraft.com" in self.driver.current_url and "login" not in self.driver.current_url:
                    self.log(">>> 登入成功確認！ <<<")
                    return
                time.sleep(1)
            self.log("等待跳轉逾時，繼續嘗試...")

        except Exception as e:
            self.log(f"登入異常: {e}")

    def run_ticket_process(self):
        driver = self.driver
        target_price = self.price_entry.get()
        ticket_amount = self.ticket_num_combo.get()
        allow_fallback = (self.fallback_var.get() == "on")

        self.log(">>> 戰鬥開始：搜尋選位頁面 <<<")
        end_time = time.time() + 30 
        in_seat_selection = False

        while time.time() < end_time and self.is_running:
            try:
                if len(driver.find_elements(By.XPATH, "//div[@class='zone'] | //ul[@class='area-list']")) > 0:
                    self.log(">>> 抵達選位頁面！ <<<")
                    in_seat_selection = True; break
                
                btns = driver.find_elements(By.XPATH, "//*[(contains(text(), '立即購票') or contains(text(), '立即訂購') or contains(@value, '立即購票')) and not(contains(text(), '流程'))]")
                for btn in btns:
                    try:
                        if "流程" in btn.text: continue
                        link = btn.get_attribute("data-href")
                        if link: driver.get(link)
                        else: driver.execute_script("arguments[0].click();", btn)
                    except: pass 
                time.sleep(0.1)
            except: pass

        if not in_seat_selection:
            self.log(">>> 逾時：無法進入選位頁面 <<<"); return

        self.log(f"搜尋: {target_price}...")
        wait_long = WebDriverWait(driver, 10)
        try:
            area_links = wait_long.until(EC.presence_of_all_elements_located((By.XPATH, "//div[@class='zone']//a | //ul[@class='area-list']//a | //a[contains(@href, 'ticket/verify')]")))
        except: area_links = []

        found_seat = False
        def try_click(el):
            try:
                if "已售完" in el.text or "暫無" in el.text or "Sold Out" in el.text: return False
                driver.execute_script("arguments[0].click();", el)
                return True
            except: return False

        for area in area_links:
            if target_price in area.text:
                if try_click(area): self.log(f"鎖定: {target_price}"); found_seat = True; break
        
        if not found_seat and allow_fallback:
            self.log("啟動備案...")
            for area in area_links:
                if try_click(area): found_seat = True; break
        
        if not found_seat: self.log(">>> 無法選到區域 <<<")

        try:
            sel = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, "//select[starts-with(@id, 'TicketForm_ticketPrice')]")))
            Select(sel).select_by_value(ticket_amount)
        except: self.log("自動選張數失敗")

        self.log("處理驗證碼...")
        if not os.path.exists('captcha'): os.makedirs('captcha')
        try:
            img_el = wait_long.until(EC.visibility_of_element_located((By.XPATH, "//img[contains(@src, 'captcha')]")))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", img_el)
            time.sleep(0.5)
            img_el.screenshot('captcha/captcha_raw.png')
            
            img = cv2.imread('captcha/captcha_raw.png')
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            ret, binary = cv2.threshold(gray, 115, 255, cv2.THRESH_BINARY)
            
            custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            pil_img = Image.fromarray(binary)
            text = pytesseract.image_to_string(pil_img, config=custom_config)
            code = text.strip().replace(" ", "")
            self.log(f"OCR: [{code}]")

            verify_input = driver.find_element(By.ID, 'TicketForm_verifyCode')
            verify_input.click(); verify_input.clear()
            if code: verify_input.send_keys(code)
            else: winsound.Beep(1000, 300); self.log("辨識為空，請手動輸入")

            try: driver.find_element(By.ID, 'TicketForm_agree').click()
            except: pass

            self.log("準備提交... (請確認驗證碼正確後手動按 Enter)")
            
            try:
                WebDriverWait(driver, 1).until(EC.alert_is_present())
                driver.switch_to.alert.accept()
                verify_input.click(); verify_input.clear()
                winsound.Beep(1000, 500); self.log("驗證碼錯誤！")
            except: pass

        except Exception as e: self.log(f"驗證碼錯誤: {e}")

if __name__ == "__main__":
    app = TicketBotApp()
    app.mainloop()