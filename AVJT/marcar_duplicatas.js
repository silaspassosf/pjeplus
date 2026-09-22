// Bookmarklet: Marcar apenas duplicatas (deixa primeira ocorrência livre)
javascript:(function(){const p=new Map();document.querySelectorAll('tr.tr-class').forEach((r,i)=>{const n=r.querySelector('b')?.textContent?.match(/\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/)?.[0];if(n){if(p.has(n)){r.querySelector('input[type="checkbox"]')?.click()}else{p.set(n,i)}}});alert(`✓ Duplicatas marcadas! ${p.size} processos únicos identificados`)})();

// Versão formatada para bookmarklet (copie a linha acima)
// Uso: Cole na barra de favoritos do navegador como URL

/* EXPLICAÇÃO:
1. Cria um Map para rastrear primeira ocorrência de cada processo
2. Percorre todas as linhas da tabela (tr.tr-class)
3. Extrai o número do processo usando regex (formato CNJ)
4. Se o número já foi visto antes (p.has(n)), marca a checkbox
5. Se é a primeira vez (else), apenas registra no Map
6. Resultado: primeira ocorrência livre, duplicatas marcadas
*/
