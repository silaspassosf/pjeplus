"""Fix.selenium_base.click_operations"""
from ..core import aguardar_e_clicar
def safe_click_no_scroll(driver, element, log=False):
    """Click without scroll"""
    try:
        driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', {view: window, bubbles: true, cancelable: true}))", element)
        return True
    except Exception:
        return False
__all__ = ['aguardar_e_clicar', 'safe_click_no_scroll']
