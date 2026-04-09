// Arquivo para registrar processos que devem ser "apagados" (não processados)
// Formato: {numero_processo: [id_doc]}

const delete_processes = {
  "1001170-62.2025.5.02.0703": ["453635444"],
  "1001590-67.2025.5.02.0703": ["57022717"],
  "1002304-27.2025.5.02.0703": ["57033322"],
  "1002306-94.2025.5.02.0703": ["57035309"],
  "1002320-78.2025.5.02.0703": ["57041188"],
  "1000028-86.2026.5.02.0703": ["57038822"],
  "1000046-10.2026.5.02.0703": ["57031680"],
  "1000055-69.2026.5.02.0703": ["57035335"],
  "1000089-44.2026.5.02.0703": ["57025442"],
  "1001653-92.2025.5.02.0703": ["453659169"],
  "1002096-43.2025.5.02.0703": ["453666777"],
  "1000531-10.2026.5.02.0703": ["453579520"],
  "1000601-27.2026.5.02.0703": ["8463877"],
  "1001979-86.2024.5.02.0703": ["453546019"],
  "1002029-15.2024.5.02.0703": ["453701958"],
  "1000093-81.2026.5.02.0703": ["8193567"],
  "1000102-43.2026.5.02.0703": ["453523117"],
  "1000175-15.2026.5.02.0703": ["453595200"]
};

module.exports = delete_processes;
javascript:(function(){const dp={"1001170-62.2025.5.02.0703":["453635444"],"1001590-67.2025.5.02.0703":["57022717"],"1002304-27.2025.5.02.0703":["57033322"],"1002306-94.2025.5.02.0703":["57035309"],"1002320-78.2025.5.02.0703":["57041188"],"1000028-86.2026.5.02.0703":["57038822"],"1000046-10.2026.5.02.0703":["57031680"],"1000055-69.2026.5.02.0703":["57035335"],"1000089-44.2026.5.02.0703":["57025442"],"1001653-92.2025.5.02.0703":["453659169"],"1002096-43.2025.5.02.0703":["453666777"],"1000531-10.2026.5.02.0703":["453579520"],"1000601-27.2026.5.02.0703":["8463877"],"1001979-86.2024.5.02.0703":["453546019"],"1002029-15.2024.5.02.0703":["453701958"],"1000093-81.2026.5.02.0703":["8193567"],"1000102-43.2026.5.02.0703":["453523117"],"1000175-15.2026.5.02.0703":["453595200"]};function matchLinha(num,hrefHtml){var entradas=dp[num];if(!entradas)return false;if(!Array.isArray(entradas))entradas=[entradas];return entradas.some(function(e){var idDoc=typeof e==="string"||typeof e==="number"?String(e).trim():String((e&&e.id_doc)||"").trim();return !!idDoc&&hrefHtml.includes("/"+idDoc+"/");});}console.log("[DEL] Iniciando seleção...");var linhas=document.querySelectorAll("tr.cdk-drag,tr[data-row],tr.ng-star-inserted");var selecionados=0;linhas.forEach(function(linha){try{var a=linha.querySelector("pje-descricao-processo a,td pje-descricao-processo a");if(!a||!a.textContent)return;var num=a.textContent.trim();if(!dp.hasOwnProperty(num))return;var aVis=linha.querySelector("a[accesskey=\"a\"]");var hrefHtml=aVis?(aVis.href||aVis.getAttribute("href")||""):"";if(!matchLinha(num,hrefHtml))return;var cb=linha.querySelector("input[type=\"checkbox\"], mat-checkbox input, input.mat-checkbox-input");if(cb){cb.click();selecionados++;var docId=hrefHtml.match(/\/documento\/(\d+)\//);console.log("[DEL] OK:",num,"| doc_id:",docId?docId[1]:"?");}}catch(e){console.error("[DEL] erro linha:",e);}});alert("Selecionados: "+selecionados+"\nClique no lixão para remover.");})();
