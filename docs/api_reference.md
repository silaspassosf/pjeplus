# Fix.py API Reference

## Core Functions

### `safe_click(driver, seletor_ou_elemento, timeout=10, by=None, log=True)`
- **Purpose**: Safely clicks an element after ensuring it's clickable
- **Used in**: atos.py, p1.py, p2.py
- **Parameters**:
  - `driver`: Selenium WebDriver instance
  - `seletor_ou_elemento`: CSS selector or WebElement
  - `timeout`: Maximum wait time (default 10s)

### `esperar_elemento(driver, seletor, timeout=10)`
- **Purpose**: Waits for element to be present and visible
- **Used in**: p2.py

### `navegar_para_tela(driver, url)`
- **Purpose**: Navigates to specified URL with error handling
- **Used in**: p2.py

### `limpar_temp_selenium()`
- **Purpose**: Cleans up temporary Selenium files
- **Used in**: m1.py
