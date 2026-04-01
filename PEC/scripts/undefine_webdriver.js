// Remove a propriedade webdriver do navigator
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});