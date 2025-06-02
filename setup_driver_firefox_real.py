from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
import time
import random

def setup_driver_firefox_perfil_real():
    profile_path = r"C:\Users\Silas\AppData\Roaming\Mozilla\Firefox\Profiles\x4fkuw2q.silas-1723037723659"
    firefox_path = r"C:\Program Files\Mozilla Firefox\firefox.exe"

    options = Options()
    options.binary_location = firefox_path

    profile = FirefoxProfile(profile_path)
    # User-Agent real do Firefox
    profile.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0")

    driver = webdriver.Firefox(firefox_profile=profile, options=options)
    # Oculta o navigator.webdriver
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

# Exemplo de uso:
if __name__ == "__main__":
    driver = setup_driver_firefox_perfil_real()
    driver.get("https://cav.receita.fazenda.gov.br/")
    time.sleep(random.uniform(2, 4))
    driver.execute_script("window.scrollBy(0, 200);")
    time.sleep(random.uniform(1, 2))
    # Continue com ações manuais/humanizadas...
    input("Pressione ENTER para sair...")
    driver.quit()
