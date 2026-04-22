/**
 * 
 * @param {string} token 
 * @returns {UsuarioPJE} tocken com as informaoes do usuario do PJE
 */
function decodeJwt(token) {
  try {
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
}

async function getPapelPessoaLogada() {
  const accessToken = getCookie("access_token");
  const payload = decodeJwt(accessToken);
  const papel = payload?.papelKz?.nome ?? payload?.papel?.nome;
  console.log("Papel:", papel);
  return papel;
}

async function getOrgaoJulgadorId() {
  const accessToken = getCookie("access_token");
  const payload = decodeJwt(accessToken);
  const codigoOJ = payload?.orgaoJulgador?.id;
  console.log("Órgão ID:", codigoOJ);
  return codigoOJ;
}

async function getOrgaoJulgadorColegiadoId() {
  const accessToken = getCookie("access_token");
  const payload = decodeJwt(accessToken);
  const codigoOJ = payload?.orgaoJulgadorColegiado?.id;
  console.log("Órgão Colegiado ID:", codigoOJ);
  return codigoOJ;
}

/**
 * @param {ProcessoPJE | ProcessoSimplificado | null | undefined} processo
 * @returns {{ idOJProcesso: (number|null), idOJCProcesso: (number|null) }}
 */
function extrairOJOJC(processo) {
  if (processo == null) return { idOJProcesso: null, idOJCProcesso: null };

  if ('orgaoJulgador' in processo) {
    // Aqui é ProcessoPJE
    return {
      idOJProcesso: processo.orgaoJulgador?.id ?? null,
      idOJCProcesso: processo.orgaoJulgadorColegiado?.id ?? null
    };
  }

  // Aqui é ProcessoSimplificado
  return {
    idOJProcesso: processo.idOrgaoJulgador ?? null,
    idOJCProcesso: processo.idOrgaoJulgadorColegiado ?? null
  };
}

/**
 * ATENÇÃO: atualmente, essa função só funciona dentro do PJE. Ver se usar no background nos permite acessar os cookies do PJE, mesmo em outro domínio.
 * Verifica se a pessoa e o processo têm o mesmo Órgão Julgador (OJ) e Órgão Julgador Colegiado (OJC) a partir do cookie do usuário.
 * @param {ProcessoPJE | ProcessoSimplificado} processo - Objeto do processo com idOJ e idOJC
 * @returns {Promise<boolean>} true se OJ e OJC coincidirem (ou ambos nulos)
 * @throws {Error} Se falhar ao obter IDs dos órgãos da pessoa
 */
async function isMesmoOJOJCProcesso(processo) {
    try {
        const idOJPessoa = await getOrgaoJulgadorId();
        const idOJCPessoa = await getOrgaoJulgadorColegiadoId();
        const {idOJProcesso, idOJCProcesso} = extrairOJOJC(processo);
        console.info('validando acesso processo', {idOJPessoa, idOJProcesso, idOJCPessoa, idOJCProcesso})

        // Lógica OJ: ambos existem e são iguais OU ambos nulos/inexistentes
        const ojCompatível = 
            (idOJPessoa != null && idOJProcesso != null && idOJPessoa === idOJProcesso) ||
            (idOJPessoa == null && idOJProcesso == null);

        // Lógica OJC: mesma regra
        const ojcCompatível = 
            (idOJCPessoa != null && idOJCProcesso != null && idOJCPessoa === idOJCProcesso) ||
            (idOJCPessoa == null && idOJCProcesso == null);

        return ojCompatível && ojcCompatível;
    } catch (error) {
        console.error('Erro ao verificar OJ/OJC:', error);
        return false;
    }
}
