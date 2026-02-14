"""SISB Core - Driver"""

try:
    from driver_config import criar_driver_sisb
except Exception:
    try:
        from Fix.drivers.lifecycle import criar_driver_sisb_pc as criar_driver_sisb
    except Exception:
        criar_driver_sisb = None


def driver_sisbajud():
    """Cria o driver para SISBAJUD usando a fabrica definida em driver_config."""
    try:
        if not criar_driver_sisb:
            print('[SISBAJUD][DRIVER] criar_driver_sisb indisponivel (driver_config ausente)')
            return None
        print('[SISBAJUD][DRIVER] Iniciando criacao do driver Firefox SISBAJUD...')
        driver = criar_driver_sisb()
        if driver:
            print('[SISBAJUD][DRIVER] Driver criado com sucesso')
        else:
            print('[SISBAJUD][DRIVER] criar_driver_sisb retornou None')
        return driver
    except Exception as e:
        print(f"[SISBAJUD][DRIVER] Erro ao criar driver SISBAJUD via driver_config: {e}")
        import traceback
        traceback.print_exc()
        return None