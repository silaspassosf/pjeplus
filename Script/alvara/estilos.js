// Script/alvara/estilos.js - CSS do painel lateral do alvara.
(function () {
    'use strict';

    const Alv = (window.Alv = window.Alv || {});
    const OVERLAY_ID = Alv.const.OVERLAY_ID;
    function estilos() {
        return `
            <style id="pje-alvara-style">
                #${OVERLAY_ID} {
                    position: fixed;
                    top: 0;
                    right: 0;
                    height: 100vh;
                    width: min(560px, 96vw);
                    z-index: 2147483647;
                    background: #f8fafc;
                    border-left: 1px solid #cbd5e1;
                    box-shadow: -10px 0 26px rgba(15, 23, 42, .18);
                    display: flex;
                    flex-direction: column;
                    font-family: Arial, sans-serif;
                }

                .pje-alvara-window {
                    flex: 1;
                    min-height: 0;
                    display: flex;
                    flex-direction: column;
                    background: #f8fafc;
                    color: #172033;
                    overflow: hidden;
                }

                .pje-alvara-header {
                    padding: 7px 12px;
                    background: #172554;
                    color: #fff;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 10px;
                }

                .pje-alvara-header h2 {
                    margin: 0;
                    font-size: 14px;
                }

                .pje-alvara-header small {
                    display: block;
                    margin-top: 2px;
                    color: #bfdbfe;
                }

                .pje-alvara-close {
                    border: 0;
                    background: transparent;
                    color: #fff;
                    font-size: 18px;
                    line-height: 1;
                    cursor: pointer;
                }

                .pje-alvara-content {
                    flex: 1;
                    min-height: 0;
                    padding: 8px 10px;
                    overflow-y: auto;
                }

                .pje-alvara-alert {
                    padding: 5px 8px;
                    margin-bottom: 6px;
                    border-radius: 5px;
                    background: #fef3c7;
                    border: 1px solid #f59e0b;
                    color: #78350f;
                    font-size: 10.5px;
                    line-height: 1.25;
                }

                .pje-alvara-pendente {
                    margin: 4px 0 6px;
                    padding: 5px 8px;
                    border: 1px solid #f59e0b;
                    border-radius: 5px;
                    background: #fffbeb;
                    color: #92400e;
                    font-size: 11px;
                    line-height: 1.3;
                }

                .pje-alvara-empty {
                    padding: 8px;
                    border: 1px dashed #94a3b8;
                    border-radius: 6px;
                    background: #fff;
                    color: #475569;
                    font-size: 12px;
                    line-height: 1.3;
                    text-align: center;
                }

                .pje-alvara-card {
                    margin-bottom: 8px;
                    padding: 7px 9px;
                    border: 1px solid #cbd5e1;
                    border-radius: 7px;
                    background: #fff;
                }

                .pje-alvara-card-header {
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    margin-bottom: 3px;
                }

                .pje-alvara-index {
                    width: 18px;
                    height: 18px;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 50%;
                    background: #2563eb;
                    color: #fff;
                    font-weight: bold;
                    font-size: 11px;
                    flex: none;
                }

                .pje-alvara-tipo {
                    flex: 1;
                    font-weight: bold;
                    font-size: 12.5px;
                    padding: 3px 6px !important;
                    margin-top: 0 !important;
                }

                .pje-alvara-card label {
                    display: block;
                    margin: 3px 0;
                    color: #334155;
                    font-size: 11px;
                    font-weight: bold;
                }

                .pje-alvara-card input,
                .pje-alvara-card select {
                    box-sizing: border-box;
                    width: 100%;
                    margin-top: 2px;
                    padding: 4px 7px;
                    border: 1px solid #94a3b8;
                    border-radius: 4px;
                    background: #fff;
                    color: #0f172a;
                    font-size: 12px;
                }

                .pje-alvara-dados {
                    margin-top: 5px;
                    padding: 6px 8px;
                    border-radius: 5px;
                    background: #f1f5f9;
                }

                .pje-alvara-dados-grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 4px 8px;
                }

                .pje-alvara-subtitle {
                    margin-bottom: 3px;
                    color: #1e3a8a;
                    font-size: 10.5px;
                    font-weight: bold;
                }

                .pje-alvara-info {
                    padding: 4px 6px;
                    margin-top: 4px;
                    border-radius: 4px;
                    background: #e2e8f0;
                    color: #475569;
                    font-size: 10.5px;
                    line-height: 1.3;
                }

                .pje-alvara-secondary {
                    margin-top: 5px;
                    padding: 4px 10px;
                    border: 1px solid #64748b;
                    border-radius: 5px;
                    background: #fff;
                    color: #334155;
                    cursor: pointer;
                    font-size: 11px;
                }

                .pje-alvara-consulta {
                    margin-top: 5px;
                    font-size: 11px;
                    line-height: 1.3;
                }

                .pje-alvara-consulta [data-consulta-link] {
                    margin-left: 6px;
                    color: #2563eb;
                }

                .pje-alvara-consulta .muted {
                    color: #64748b;
                }

                .pje-alvara-consulta .ok {
                    color: #15803d;
                }

                .pje-alvara-consulta .warn {
                    color: #b45309;
                }

                .pje-alvara-consulta .erro {
                    color: #b91c1c;
                }

                .pje-alvara-secondary:hover {
                    background: #e2e8f0;
                }

                .pje-alvara-footer {
                    display: flex;
                    flex-direction: column;
                    align-items: stretch;
                    gap: 5px;
                    padding: 7px 10px;
                    border-top: 1px solid #cbd5e1;
                    background: #f1f5f9;
                }

                .pje-alvara-add-row {
                    display: flex;
                    gap: 6px;
                    align-items: stretch;
                }

                .pje-alvara-add-select {
                    flex: 1;
                    padding: 5px 8px;
                    border: 1px solid #94a3b8;
                    border-radius: 5px;
                    background: #fff;
                    color: #0f172a;
                    font-size: 12px;
                    box-sizing: border-box;
                }

                .pje-alvara-add {
                    padding: 5px 12px;
                    border: 0;
                    border-radius: 5px;
                    background: #2563eb;
                    color: #fff;
                    font-weight: bold;
                    cursor: pointer;
                    font-size: 12px;
                    flex: none;
                }

                .pje-alvara-add:hover {
                    background: #1d4ed8;
                }

                .pje-alvara-status {
                    color: #475569;
                    font-size: 10.5px;
                    text-align: center;
                }

                .pje-alvara-primary {
                    width: 100%;
                    padding: 7px 12px;
                    border: 0;
                    border-radius: 5px;
                    background: #16a34a;
                    color: #fff;
                    font-weight: bold;
                    cursor: pointer;
                    box-sizing: border-box;
                    font-size: 13px;
                }

                .pje-alvara-primary:hover {
                    background: #15803d;
                }

                .pje-alvara-origem {
                    margin: 0 0 4px;
                    color: #64748b;
                    font-size: 10px;
                    font-style: italic;
                }

                .pje-alvara-remove {
                    padding: 2px 7px;
                    border: 1px solid #dc2626;
                    border-radius: 4px;
                    background: #fff;
                    color: #b91c1c;
                    cursor: pointer;
                    font-size: 10.5px;
                    flex: none;
                }

                .pje-alvara-remove:hover {
                    background: #fee2e2;
                }

                @media (max-width: 700px) {
                    .pje-alvara-dados-grid {
                        grid-template-columns: 1fr;
                    }
                }
            </style>
        `;
    }

    Alv.estilos = { estilos: estilos };
})();
