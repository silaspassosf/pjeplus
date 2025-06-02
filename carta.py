from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
from datetime import datetime
import re
from Fix import extrair_dados_processo  # For getting process number

def def_carta(driver, log=True):
    """
    Automates the eCarta consultation process:
    1. Finds target notifications in the timeline
    2. Extracts process number and notification IDs
    3. Consults eCarta system
    4. Copies relevant data
    5. Attaches results using anexos.py
    """
    try:
        # Store found notification IDs and their data
        notification_data = []
        
        # 1. Find and process notifications
        # Look for notifications in the document list (not timeline)
        notifications = driver.find_elements(By.CSS_SELECTOR, "tr.mat-row")
        latest_date = None
        
        for notification in notifications:
            try:
                # Get date from the notification row
                date_text = notification.find_element(By.CSS_SELECTOR, "td.mat-column-data").text.strip()
                current_date = datetime.strptime(date_text, "%d/%m/%Y")
                
                # Update latest date if needed
                if not latest_date or current_date > latest_date:
                    latest_date = current_date
                
                # Get notification ID and check content
                notification_id = notification.get_attribute("id")
                if not notification_id:
                    continue
                
                # Click to open notification details
                detail_btn = notification.find_element(By.CSS_SELECTOR, "[mattooltip*='Detalhes do Processo']")
                driver.execute_script("arguments[0].click();", detail_btn)
                time.sleep(1)
                
                # Switch to new tab if opened
                new_tab = None
                for handle in driver.window_handles:
                    if handle != driver.current_window_handle:
                        new_tab = handle
                        break
                
                if new_tab:
                    driver.switch_to.window(new_tab)
                    
                    # Check if content contains "eCarta REG"
                    content = driver.find_element(By.CSS_SELECTOR, "pre#textoDocumento").text
                    if "eCarta REG" in content:
                        # Store notification data
                        notification_data.append({
                            "id": notification_id,
                            "date": date_text,
                            "content": content
                        })
                    
                    # Close tab and switch back
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
            
            except Exception as e:
                if log:
                    print(f"[CARTA] Error processing notification: {str(e)}")
                continue
        
        if not notification_data:
            if log:
                print("[CARTA] No relevant notifications found")
            return False
            
        # 2. Get process number using extrair_dados_processo
        process_data = extrair_dados_processo(driver)
        if not process_data or 'numero' not in process_data:
            if log:
                print("[CARTA] Could not extract process number")
            return False
            
        process_number = process_data['numero']
        
        # 3. Access eCarta in new window
        ecarta_url = f"https://aplicacoes1.trt2.jus.br/eCarta-web/consultarProcesso.xhtml?codigo={process_number}"
        
        # Open new window for eCarta
        original_window = driver.current_window_handle
        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[-1])
        driver.get(ecarta_url)
        
        # 4. Login to eCarta if needed
        try:
            username_field = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#input_user"))
            )
            if username_field:
                username_field.send_keys("s164283")
                driver.find_element(By.CSS_SELECTOR, "#input_password").send_keys("59Justdoit!1")
                driver.find_element(By.CSS_SELECTOR, "input.btn").click()
                time.sleep(2)  # Wait for login
        except TimeoutException:
            # No login needed or already logged in
            pass
            
        # 5. Search for notification IDs and copy relevant data
        ecarta_data = []
        try:
            # Wait for results table
            table = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.table"))
            )
            
            # Get all rows
            rows = table.find_elements(By.CSS_SELECTOR, "tr")
            for notification in notification_data:
                for row in rows:
                    if notification["id"] in row.text:
                        ecarta_data.append(row.text)
                        break
                        
        except Exception as e:
            if log:
                print(f"[CARTA] Error extracting eCarta data: {str(e)}")
        
        # Close eCarta window and switch back
        driver.close()
        driver.switch_to.window(original_window)
        
        # 6. Call anexos.py def_carta function with collected data
        if ecarta_data:
            try:
                from anexos import def_carta as anexos_def_carta
                anexos_def_carta(driver, ecarta_data)
            except Exception as e:
                if log:
                    print(f"[CARTA] Error calling anexos.def_carta: {str(e)}")
                return False
        
        return True
        
    except Exception as e:
        if log:
            print(f"[CARTA] General error in def_carta: {str(e)}")
        return False