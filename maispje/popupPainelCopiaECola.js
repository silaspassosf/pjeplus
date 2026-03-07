iniciar();

async function iniciar() {
    browser.storage.local.get('processo_memoria', function(result){
        criarPainelComDadosDaMemoria(result.processo_memoria);
    });   
}

async function criarPainelComDadosDaMemoria(processo_memoria) {

    let tabela = document.createElement('div');
    let containerUL = document.createElement('ul')
    let liDadosProcesso = document.createElement('li')
    let dadosProcesso = document.createElement('dadosProcesso')
    dadosProcesso.setAttribute('ocultar',false)
    dadosProcesso.appendChild(inserirLinha('DADOS DO PROCESSO','dadosprocesso'));
    dadosProcesso.appendChild(inserirLinha('Número do Processo','comum negrito'));
    dadosProcesso.appendChild(inserirLinha(processo_memoria.numero,'selecionavel recuado','Número do processo com formatação'));
    dadosProcesso.appendChild(inserirLinha(processo_memoria.numero.replace(/\D/g,""),'selecionavel recuado opcao','Número do processo sem formatação'));

    let valor_formatado_para_uso = Intl.NumberFormat('pt-br', {style: 'decimal', currency: 'BRL'}).format(processo_memoria.divida.valor);
    let valor_formatado_para_exibir_sem_data = Intl.NumberFormat('pt-br', {style: 'currency', currency: 'BRL'}).format(processo_memoria.divida.valor);
    let valor_formatado_para_exibir_com_data = valor_formatado_para_exibir_sem_data + " em " + processo_memoria.divida.data;
    let extenso = porExtenso(valor_formatado_para_exibir_sem_data);
    
    let valor_formatado_comExtenso = valor_formatado_para_exibir_sem_data + ' (' + extenso + ')';
    dadosProcesso.appendChild(inserirLinha('Total da Execução','comum negrito'));		
    if (processo_memoria.divida.valor <= 0) {
        dadosProcesso.appendChild(inserirLinha('não há registro','selecionavel recuado'));
    } else {
        dadosProcesso.appendChild(inserirLinha(valor_formatado_para_exibir_com_data,'selecionavel recuado','Valor da execução formatado com data da atualização'));					
        dadosProcesso.appendChild(inserirLinha(valor_formatado_para_exibir_sem_data,'selecionavel recuado opcao','Valor da execução formatado'));
        dadosProcesso.appendChild(inserirLinha(valor_formatado_para_uso,'selecionavel recuado opcao','Valor da execução sem formatação'));
        dadosProcesso.appendChild(inserirLinha(valor_formatado_comExtenso,'selecionavel recuado opcao','Valor da execução formatado e por extenso'));
    }
    dadosProcesso.appendChild(inserirLinha('Justiça Gratuita','comum negrito'));
    if (processo_memoria.justicaGratuita[1] == '---') {
        dadosProcesso.appendChild(inserirLinha('não há registro','selecionavel recuado'));
    } else {
        dadosProcesso.appendChild(inserirLinha(processo_memoria.justicaGratuita[0] + ', decidido em: ' + processo_memoria.justicaGratuita[1],'selecionavel recuado'));
    }
    dadosProcesso.appendChild(inserirLinha('Transito em Julgado','comum negrito'));
    if (processo_memoria.transito == '---') {
        dadosProcesso.appendChild(inserirLinha('não há registro','selecionavel recuado'));
    } else {
        dadosProcesso.appendChild(inserirLinha(processo_memoria.transito,'selecionavel recuado'));
    }
    dadosProcesso.appendChild(inserirLinha('Custas arbitradas','comum negrito'));		
    if (processo_memoria.custas == 'R$ ---') {
        dadosProcesso.appendChild(inserirLinha('não há registro','selecionavel recuado'));
    } else {
        dadosProcesso.appendChild(inserirLinha(processo_memoria.custas,'selecionavel recuado'));
    }
    liDadosProcesso.appendChild(dadosProcesso)
    containerUL.appendChild(liDadosProcesso)


    
    let liAtivo = document.createElement('li')		
    // //MONTAGEM DO POLO ATIVO
    let poloAtivo = document.createElement('poloAtivo')
    poloAtivo.setAttribute('ocultar',false)
    let i = 1;
    poloAtivo.appendChild(inserirLinha('POLO ATIVO','poloativo'));
    let map1 = [].map.call(
        processo_memoria.autor, 
        function(parte) {
            //cria o submenu com os autores
            poloAtivo.appendChild(inserirLinha(i + 'º Reclamante:','comum negrito'));
            i++;
            let nomeA = parte.nome;
            let cpfA = (parte.cpfcnpj == "" ? "desconhecido" : parte.cpfcnpj);
            let dtNasc = parte.dataNascimento.replace( /\-/g,'/');
            dtNasc = new Date(dtNasc).toLocaleDateString();

            poloAtivo.appendChild(inserirLinha(nomeA,'selecionavel pai negrito recuado','Nome completo'));//só nome
            poloAtivo.appendChild(inserirLinha(cpfA,'selecionavel recuado  ','CPF/CNPJ'));//só cpf
            poloAtivo.appendChild(inserirLinha(cpfA.replace(/\D/g,""),'selecionavel recuado opcao','apenas números do CPF/CNPJ'));//cpf só números
            poloAtivo.appendChild(inserirLinha(nomeA + " (CPF/CNPJ " + cpfA + ")",'selecionavel recuado opcao','Nome completo com CPF/CNPJ'));//nome e CPF
            poloAtivo.appendChild(inserirLinha('Nasc: ' + dtNasc,'selecionavel italico recuado opcao','Data de Nascimento'));//data nascimento
            poloAtivo.appendChild(inserirLinha('Mãe: ' + parte.nomeGenitora,'selecionavel italico recuado opcao','Nome da Mãe'));//nome genitora
            
            //cria o submenu com os advogados do autor
            if (!parte.representantes) { return }
            if (parte.representantes.length == 0) {
                // poloAtivo.appendChild(inserirLinha('Endereço:','representante negrito recuado'));
                // poloAtivo.appendChild(inserirLinha('domicilioEletronico','selecionavel procurador opcao','teste'));
            } else {
                poloAtivo.appendChild(inserirLinha('Advogados:','representante negrito recuado'));
                let map1a = [].map.call(
                    parte.representantes, 
                    function(representante) {
                        let nomeAR = representante.nome;
                        let cpfAR = (representante.cpfcnpj == "" ? "desconhecido" : representante.cpfcnpj);
                        let oabAR = representante.oab == "" ? "desconhecido" : representante.oab;
                        poloAtivo.appendChild(inserirLinha(nomeAR + " (OAB/" + oabAR + ")",'selecionavel pai procurador','Nome completo com OAB'));//nome e OAB
                        poloAtivo.appendChild(inserirLinha(nomeAR + " (CPF/CNPJ " + cpfAR + ")",'selecionavel procurador opcao','Nome completo com CPF/CNPJ'));//nome e CPF
                        poloAtivo.appendChild(inserirLinha(nomeAR,'selecionavel procurador opcao','Nome completo'));//só nome
                        poloAtivo.appendChild(inserirLinha(cpfAR,'selecionavel procurador opcao','CPF/CNPJ'));//só cpf
                        poloAtivo.appendChild(inserirLinha("OAB/" + oabAR,'selecionavel procurador opcao','OAB'));//só OAB											
                    }
                );
            }
        }
    );
    liAtivo.appendChild(poloAtivo)
    containerUL.appendChild(liAtivo)

    let liPassivo = document.createElement('li')

    // //MONTAGEM DO POLO PASSIVO
    let poloPassivo = document.createElement('poloPassivo')
    poloPassivo.setAttribute('ocultar',false)
    let i2 = 1;
    poloPassivo.appendChild(inserirLinha('POLO PASSIVO','polopassivo'));
    let map2 = [].map.call(
        processo_memoria.reu, 
        function(parte) {
            //cria o submenu com os autores
            poloPassivo.appendChild(inserirLinha(i2 + 'º Reclamado:','comum negrito'));
            i2++;
            let nomeA = parte.nome;
            let cpfA = (parte.cpfcnpj == "" ? "desconhecido" : parte.cpfcnpj);

            poloPassivo.appendChild(inserirLinha(nomeA,'selecionavel pai negrito recuado','Nome completo', parte.id));//só nome
            poloPassivo.appendChild(inserirLinha(cpfA,'selecionavel recuado ','CPF/CNPJ'));//só cpf
            poloPassivo.appendChild(inserirLinha(cpfA.replace(/\D/g,""),'selecionavel recuado opcao','apenas números do CPF/CNPJ'));//cpf só números
            poloPassivo.appendChild(inserirLinha(nomeA + " (CPF/CNPJ " + cpfA + ")",'selecionavel recuado opcao','Nome completo com CPF/CNPJ'));//nome e CPF
            

            //cria o submenu com os advogados do reu
            if (!parte.representantes) { return }
            if (parte.representantes.length == 0) {
                poloPassivo.appendChild(inserirLinha('Endereço:','representante negrito recuado'));

                let elDomicilio = document.createElement('domicilio');
                elDomicilio.classList.add('carregando');
                // elDomicilio.style.display = 'none';
                elDomicilio.setAttribute('maisPje',parte.id);
                poloPassivo.appendChild(elDomicilio);

                if (parte.endereco) {                    
                    let elEndereco = document.createElement('endereco');
                    elEndereco.classList.add('carregando');
                    // elEndereco.style.display = 'none';
                    elEndereco.setAttribute('maisPje', parte.id + '|' + parte.endereco);                    
                    poloPassivo.appendChild(elEndereco);
                }
                
            } else {
                poloPassivo.appendChild(inserirLinha('Advogados:','representante negrito recuado'));
                let map2a = [].map.call(
                    parte.representantes, 
                    function(representante) {
                        let nomeAR = representante.nome;
                        let cpfAR = (representante.cpfcnpj == "" ? "desconhecido" : representante.cpfcnpj);
                        let oabAR = representante.oab == "" ? "desconhecido" : representante.oab;
                        poloPassivo.appendChild(inserirLinha(nomeAR + " (OAB/" + oabAR + ")",'selecionavel pai procurador','Nome completo com OAB'));//nome e OAB
                        poloPassivo.appendChild(inserirLinha(nomeAR + " (CPF/CNPJ " + cpfAR + ")",'selecionavel procurador opcao','Nome completo com CPF/CNPJ'));//nome e CPF
                        poloPassivo.appendChild(inserirLinha(nomeAR,'selecionavel procurador opcao','Nome completo'));//só nome
                        poloPassivo.appendChild(inserirLinha(cpfAR,'selecionavel procurador opcao','CPF/CNPJ'));//só cpf
                        poloPassivo.appendChild(inserirLinha("OAB/" + oabAR,'selecionavel procurador opcao','OAB'));//só OAB
                    }
                );
            }
        }
    );
    
    liPassivo.appendChild(poloPassivo)
    containerUL.appendChild(liPassivo)

    if (processo_memoria.terceiro.length > 0) {
        let liTerceiro = document.createElement('li')
        // //MONTAGEM DOS TERCEIROS
        // console.log(processo_memoria.terceiro.length)
        let poloOutros = document.createElement('poloOutros')
        poloOutros.setAttribute('ocultar',false)
        let i3 = 1;
        if (!processo_memoria.terceiro) { return }
        poloOutros.appendChild(inserirLinha('OUTROS INTERESSADOS','polooutros'));
        let map3 = [].map.call(
            processo_memoria.terceiro, 
            function(parte) {
                //cria o submenu com os autores
                poloOutros.appendChild(inserirLinha(i3 + 'º Terceiro:','comum negrito'));
                i3++;
                let nomeA = parte.nome;
                let cpfA = (parte.cpfcnpj == "" ? "desconhecido" : parte.cpfcnpj);

                poloOutros.appendChild(inserirLinha(nomeA,'selecionavel pai negrito recuado','Nome completo'));//só nome
                poloOutros.appendChild(inserirLinha(cpfA,'selecionavel recuado ','CPF/CNPJ'));//só cpf
                poloOutros.appendChild(inserirLinha(cpfA.replace(/\D/g,""),'selecionavel recuado opcao','apenas números do CPF/CNPJ'));//cpf só números
                poloOutros.appendChild(inserirLinha(nomeA + " (CPF/CNPJ " + cpfA + ")",'selecionavel recuado opcao','Nome completo com CPF/CNPJ'));//nome e CPF

                //cria o submenu com os advogados do autor
                if (!parte.representantes) { return }
                poloOutros.appendChild(inserirLinha('Advogados:','representante negrito recuado'));
                let map3a = [].map.call(
                    parte.representantes, 
                    function(representante) {
                        let nomeAR = representante.nome;
                        let cpfAR = (representante.cpfcnpj == "" ? "desconhecido" : representante.cpfcnpj);
                        let oabAR = representante.oab == "" ? "desconhecido" : representante.oab;
                        poloOutros.appendChild(inserirLinha(nomeAR + " (OAB/" + oabAR + ")",'selecionavel pai procurador','Nome completo com OAB'));//nome e OAB
                        poloOutros.appendChild(inserirLinha(nomeAR + " (CPF/CNPJ " + cpfAR + ")",'selecionavel  procurador opcao','Nome completo com CPF/CNPJ'));//nome e CPF
                        poloOutros.appendChild(inserirLinha(nomeAR,'selecionavel procurador opcao','Nome completo'));//só nome
                        poloOutros.appendChild(inserirLinha(cpfAR,'selecionavel procurador opcao','CPF/CNPJ'));//só cpf
                        poloOutros.appendChild(inserirLinha("OAB/" + oabAR,'selecionavel procurador opcao','OAB'));//só OAB
                    }
                );				
            }
        );
        liTerceiro.appendChild(poloOutros)
        containerUL.appendChild(liTerceiro)
    }

    tabela.appendChild(containerUL);
    document.body.appendChild(tabela);	
    
    function inserirLinha(valor, classe='comum', title='', domicilio='') {
        let span = document.createElement('span');
        span.title = title;
        if (domicilio) { span.setAttribute('idPessoa',domicilio) }
        span.className = classe;
        span.innerText = valor;
        return span;
    }

}
