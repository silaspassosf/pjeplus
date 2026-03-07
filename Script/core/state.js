(function () {
    'use strict';

    // ── CleanupRegistry ──────────────────────────────────────────────
    // Rastreia TODOS os recursos criados (event listeners, intervals,
    // timeouts, observers, channels) e os libera em dispose().
    class CleanupRegistry {
        #items = [];

        add(fn) {
            this.#items.push(fn);
            // Retorna função de cancelamento individual
            return () => {
                const i = this.#items.indexOf(fn);
                if (i !== -1) this.#items.splice(i, 1);
            };
        }

        // Listeners com remoção automática
        on(target, type, fn, opts) {
            target.addEventListener(type, fn, opts);
            return this.add(() => target.removeEventListener(type, fn, opts));
        }

        // setInterval com limpeza
        interval(fn, ms) {
            const id = setInterval(fn, ms);
            return this.add(() => clearInterval(id));
        }

        // setTimeout com limpeza (se ainda não disparou)
        timeout(fn, ms) {
            const id = setTimeout(fn, ms);
            return this.add(() => clearTimeout(id));
        }

        // MutationObserver
        observer(obs) {
            return this.add(() => obs.disconnect());
        }

        // BroadcastChannel
        channel(ch) {
            return this.add(() => { try { ch.close(); } catch (e) { } });
        }

        dispose() {
            // Inverte a ordem para desfazer na ordem oposta à criação
            [...this.#items].reverse().forEach(fn => { try { fn(); } catch (e) { } });
            this.#items = [];
        }
    }

    // ── AsyncRunner ───────────────────────────────────────────────────
    // Garante que apenas uma operação assíncrona rode por vez.
    // Cancela a anterior ao iniciar nova (via AbortSignal).
    class AsyncRunner {
        #ctrl = null;

        get running() { return !!this.#ctrl; }

        async run(fn) {
            this.abort();
            this.#ctrl = new AbortController();
            const signal = this.#ctrl.signal;
            try {
                await fn(signal);
            } catch (e) {
                if (e?.name !== 'AbortError') throw e;
            } finally {
                this.#ctrl = null;
            }
        }

        abort() {
            this.#ctrl?.abort(new DOMException('Cancelled', 'AbortError'));
            this.#ctrl = null;
        }
    }

    // ── Estado global ─────────────────────────────────────────────────
    // Singleton reutilizado entre navegações SPA.
    // dispose() é chamado pelo orchestrator a cada pushState.

    if (!window._pjeTools) {
        window._pjeTools = {
            // Módulo lista
            lista: {
                docs: null,          // cache da timeline
                readAt: 0,           // timestamp da última leitura
                runner: new AsyncRunner(),
            },
            // Módulo atalhos
            atalhos: {
                channel: null,
                registry: new CleanupRegistry(),
            },
            // Módulo infojud
            infojud: {
                fila: [],
                atual: 0,
                modo: '',
                dados: [],
                runner: new AsyncRunner(),
            },
            // Registro global (listeners do painel, etc.)
            registry: new CleanupRegistry(),
            _iniciado: false,

            dispose() {
                this.lista.docs = null;
                this.lista.readAt = 0;
                this.lista.runner.abort();

                this.infojud.runner.abort();
                this.infojud.fila = [];
                this.infojud.atual = 0;
                this.infojud.dados = [];

                this.atalhos.registry.dispose();

                this.registry.dispose();
                this._iniciado = false;

                // Remove painéis injetados
                ['pjetools-painel', 'listaDocsExecucaoSimples',
                    'listaDocsEditalSimples', 'god-relatorio-panel',
                    'pjetools-toast'].forEach(id => document.getElementById(id)?.remove());

                // Remove atributo de boot (permite reinjeção após navigate)
                document.documentElement.removeAttribute('data-pjetools-boot');
            },
        };
    }

    const PJeState = window._pjeTools;

    // Exports
    window.PJeState = PJeState;
    window.CleanupRegistry = CleanupRegistry;
    window.AsyncRunner = AsyncRunner;
})();