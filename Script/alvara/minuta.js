// Script/alvara/minuta.js — GANCHO DA FASE 2 (SISCONDJ).
//
// PLACEHOLDER DEFINITIVO: este módulo NÃO muda mais na fase 1.
// Ele é o ponto de entrada do processo seguinte, chamado pelo botão
// "Criar alvarás" do overlay. Quando a fase 2 (SISCONDJ) for implementada,
// a lógica real entra DENTRO de iniciarFluxoMinuta(), sem alterar o contrato:
//
//     Alv.minuta.iniciarFluxoMinuta(estado) -> { iniciado: boolean, motivo?: string }
//
// Contrato do `estado` recebido (congelado — ver PLANO-MODULAR.md):
// {
//     processo: { numero, partes: { ativo, passivo, outros }, peritos },
//     itens: [ { id, tipo, valor, valorFixo, destinoTipo, destinatarioNome,
//                destinatarioDocumento, dados: { banco, agencia, conta, tipoConta },
//                deposito, transferencia, siscon } ]
// }

(function () {
    'use strict';

    const Alv = (window.Alv = window.Alv || {});

    function validarEstado(estado) {
        if (!estado) return 'estado ausente';
        if (!Array.isArray(estado.itens) || estado.itens.length === 0) {
            return 'nenhuma verba no estado';
        }
        return null;
    }

    function iniciarFluxoMinuta(estado) {
        const erro = validarEstado(estado);

        if (erro) {
            console.warn('[PjeAlvara][minuta] fluxo nao iniciado:', erro);
            return { iniciado: false, motivo: erro };
        }

        // ── FASE 2 (SISCONDJ) — implementar aqui: ────────────────────────
        // 1. Abrir/verificar aba do SISCONDJ com a sessao do usuario.
        // 2. Selecionar o fluxo correspondente ao tipo de cada item
        //    (estado.itens[].tipo -> fluxo do SISCONDJ).
        // 3. Preencher os campos que aparecerem na tela (fase 2 le a tela
        //    via Alv.siscondj.extrairDadosSiscondj()).
        // 4. Usar dados bancarios do item (dados.banco/agencia/conta/tipoConta)
        //    e destinatario (destinatarioNome/destinatarioDocumento).
        // ──────────────────────────────────────────────────────────────────

        console.log('[PjeAlvara][minuta] placeholder — fase 2 SISCONDJ ainda nao implementada.');
        console.log('[PjeAlvara][minuta] estado recebido com', estado.itens.length, 'verba(s).');

        return { iniciado: false, motivo: 'fase 2 (SISCONDJ) nao implementada' };
    }

    Alv.minuta = { iniciarFluxoMinuta: iniciarFluxoMinuta };
})();
