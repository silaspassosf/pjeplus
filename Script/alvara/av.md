Alvará autor - conta do advogado

<table id="tiposFinalidades" class="formulario">
                        <tbody id="tbodyFormAlvara">
                           
                                <tr id="trTipoFinalidade">                                  
                                        <td class="titulo">Tipo de Finalidade*</td>
                                        <td>
                                            <select id="cb_tipoFinalidade" name="tipoFinalidade" style="min-width: 100px; display: none;" onchange="abrirLinhasFinalidades();">
                                                        <option value="">Selecione...</option>
                                                        <option value="SAQUE_AGENCIA_BB">Comparecer ao Banco</option><option value="CREDITO_CONTA_BB">Crédito em Conta no Banco do Brasil</option><option value="CREDITO_CONTA_OUTRO_BANCO">Crédito em Conta para Outros Bancos</option><option value="PIX">Pix</option><option value="PAGAMENTO_GUIA">Pagamento de Guia</option><option value="TED_JUDICIAL">TED Judicial</option><option value="DARF">Pagamento de DARF</option><option value="GRU">Pagamento de GRU</option><option value="GPS">Pagamento de GPS</option><option value="NOVO_DEPOSITO">Novo Depósito Judicial</option>								
                                                </select><div class="chosen-container chosen-container-single" style="width: 280px;" title="" id="cb_tipoFinalidade_chosen"><a class="chosen-single" tabindex="-1"><span>Crédito em Conta para Outros Bancos</span><div><b></b></div></a><div class="chosen-drop"><div class="chosen-search"><input type="text" autocomplete="off"></div><ul class="chosen-results"><li class="active-result result-selected" style="" data-option-array-index="0">Selecione...</li><li class="active-result" style="" data-option-array-index="1">Comparecer ao Banco</li><li class="active-result" style="" data-option-array-index="2">Crédito em Conta no Banco do Brasil</li><li class="active-result result-selected" style="" data-option-array-index="3">Crédito em Conta para Outros Bancos</li><li class="active-result" style="" data-option-array-index="4">Pix</li><li class="active-result" style="" data-option-array-index="5">Pagamento de Guia</li><li class="active-result" style="" data-option-array-index="6">TED Judicial</li><li class="active-result" style="" data-option-array-index="7">Pagamento de DARF</li><li class="active-result" style="" data-option-array-index="8">Pagamento de GRU</li><li class="active-result" style="" data-option-array-index="9">Pagamento de GPS</li><li class="active-result" style="" data-option-array-index="10">Novo Depósito Judicial</li></ul></div></div>
                                                <span id="cb_tipoFinalidade_errors" class="invisivel">Campo obrigatorio</span>
                                                
                                        </td>
                                </tr>
                        
                                
                                        
                                        
                                        
                                                


























<!-- Formulario de selecao de autor e reu

OBS: Passar o nome da classe via jsp:param.
-->

<tr id="linhaTipoBeneficiario" class="finalidade_credito_outros_bancos">
        <td class="titulo">Tipo de Beneficiário*</td>
        <td>
            <input type="hidden" id="beneficiario_id" name="beneficiario.id" value="51426259">
            <input type="hidden" id="beneficiario_pessoa_nome" name="beneficiario.pessoa.nome" value="SELMA MARIA DOMINGOS">
            <input type="hidden" id="beneficiario_pessoa_cpfCnpj" name="beneficiario.pessoa.cpfCnpj" value="21997471825">
            <input type="hidden" id="beneficiario_parte_principal" name="beneficiario.pessoa.principal" value="false">
            <input type="hidden" id="beneficiario_papel" name="beneficiario.papel" value="RECLAMANTE">
            <input type="hidden" id="beneficiario_processo" name="beneficiario.processo.id" value="11073364">
            
            <div id="camposBeneficiario">    <input type="hidden" id="21997471825" value="21997471825;SELMA MARIA DOMINGOS;false;RECLAMANTE"><input type="hidden" id="21997471825" value="21997471825;SELMA MARIA DOMINGOS;false;RECLAMANTE"></div>
            
        <select id="cb_tipoBeneficiario" name="tipoBeneficiario" style="min-width: 150px; display: none;" onchange="cbTipoBeneficiarioChange()">
			<option value="">Selecione...</option>
                        
                                <option value="10" papel="ADV_RECLAMADO" tipo="ADVOGADO">Adv Réu</option>
                        
                                <option value="9" papel="ADV_RECLAMANTE" tipo="ADVOGADO">Adv Autor</option>
                        
                                <option value="5" papel="RECLAMADO" tipo="REU">Réu</option>
                        
                                <option value="1" papel="RECLAMANTE" tipo="AUTOR">Autor</option>
                        
                                <option value="11" papel="TERCEIRO" tipo="OUTROS">Terceiro</option>
                        
		</select><div class="chosen-container chosen-container-single" style="width: 203px;" title="" id="cb_tipoBeneficiario_chosen"><a class="chosen-single" tabindex="-1"><span>Autor</span><div><b></b></div></a><div class="chosen-drop"><div class="chosen-search"><input type="text" autocomplete="off"></div><ul class="chosen-results"><li class="active-result result-selected" style="" data-option-array-index="0">Selecione...</li><li class="active-result" style="" data-option-array-index="1">Adv Réu</li><li class="active-result" style="" data-option-array-index="2">Adv Autor</li><li class="active-result" style="" data-option-array-index="3">Réu</li><li class="active-result result-selected" style="" data-option-array-index="4">Autor</li><li class="active-result" style="" data-option-array-index="5">Terceiro</li></ul></div></div>
                <input type="hidden" id="beneficiarioTransiente">
                <input type="hidden" id="beneficiario" name="beneficiario.id" value="">
                <span id="cb_tipoBeneficiario_errors" class="invisivel">Campo obrigatorio</span>
                  
                <input type="hidden" id="qtdeBeneficiarios" name="qtdeBeneficiarios">
        </td>
</tr>
<tr id="linhaBeneficiario" style="" class="finalidade_credito_outros_bancos">
        
        <td class="titulo">
                Beneficiário*
        </td>
        <td id="colunaBeneficiario">
        	<div id="divBeneficiario">
	            <select id="comboBeneficiario" onchange="verificarBeneficiarioSelecionado();setarHiddens(this.value)" style="display: none;"><option value="0" selected="selected">Selecione...</option><option value="21997471825" cpf="21997471825">SELMA MARIA DOMINGOS </option></select><div class="chosen-container chosen-container-single" style="width: 450px; display: inline-block;" title="" id="comboBeneficiario_chosen"><a class="chosen-single" tabindex="-1"><span>SELMA MARIA DOMINGOS</span><div><b></b></div></a><div class="chosen-drop"><div class="chosen-search"><input type="text" autocomplete="off"></div><ul class="chosen-results"><li class="active-result" style="" data-option-array-index="0">Selecione...</li><li class="active-result result-selected" style="" data-option-array-index="1">SELMA MARIA DOMINGOS </li></ul></div></div>   
	            
            </div>
        </td>
</tr>
<tr id="linha_beneficiario_cpfCnpj" class="finalidade_credito_outros_bancos" style="opacity: 1; display: table-row;">
        <td id="tituloBeneficiario_cpfCnpj" class="titulo">
                
                        
                              CPF/CNPJ do Beneficiário
                        
                        
                
                









<span title="Preencha o CPF ou CNPJ sem formatação." class="bt-acao-ajuda"> </span>
        </td>
        <td>
		

































        
        
<div style="float:left">
	<input id="solicitacaoTransiente_beneficiario_pessoa_cpfCnpj" name="solicitacaoTransiente.beneficiario.pessoa.cpfCnpj" onkeydown="Mascara(this,CpfCnpjContagem);" onblur="validaCpfCnpj_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj();byPassCpfCnpjBeneficiarioConta();" onchange="Mascara(this,CpfCnpjContagem);" type="text" value="" size="40" maxlength="18">
	





















<input type="button" id="solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button" class="botaoAtualizar invisivel" value="Validar" onclick="executarAcao_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button()">

<script type="text/javascript">

	function executarAcao_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button(){
				
                
	            var retorno = true;

                
                        retorno = validaCpfCnpj_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj();
                
        
                
                        
                if(retorno) {
                        
                }
	}
</script>

	<span id="span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj" class="fieldWithErrors invisible"></span>
	
        <br>
        <label id="lb_msg_cpf_cnpj_quantidade_digitos" style="color:#555555; font-size:10px;">(Informe 11 (onze) digitos para CPF ou 14 (quatorze) para CNPJ)</label>
</div>
<script type="text/javascript">
function validaCpfCnpj_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj() {
        $("#solicitacaoTransiente_beneficiario_pessoa_nome").val("");
	var cpfCnpj = Integer($("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val());
	cpfCnpj = cpfCnpj.replace(/[-./]/g, '');
	if(cpfCnpj == "") {
		
		    $("#solicitacaoTransiente_beneficiario_pessoa_nome").val("");
		    
		    
		    
		    $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('invisible');
		    $("#tribunais_ajaxGif_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button").hide();
		    $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button").removeAttr("disabled");
		
		return true;
	}

	if("CPFCNPJ" === 'CPFCNPJ'){

		if($("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val().length!=14 && $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val().length!=18){
		            aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	if("CPFCNPJ" === 'CPF'){

		if($("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val().length!=14){
		            aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	if("CPFCNPJ" === 'CNPJ'){

		if($("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val().length!=18){
		            aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	
	$("#tribunais_ajaxGif_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button").show();
		
	// realiza chamada WS
	$("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").trigger("eventIniciarRequisicaoAjax");
        
        
        //validar cpfcnpj nas partes do processo e no bb ou somento no bb
        if(true){
                var opt = $("#cb_tipoBeneficiario > option:checked");
                var tipo = opt.attr('tipo');
                var url = "/portaltrtsp/pages/processo/tribunal/"+$("#numeroProcesso").val()+"/cpfcnpj/"+cpfCnpj+"/"+tipo+"/validar.json";
        }else{      
                var url = "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validarModulo.json";
                
                        url = "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validar.json";
                
        }
        
        var ajaxReq = $.ajax(url, {
                dataType: "text",

                statusCode: {
                        200: function() { 
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldWithErrors');
                                aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("");
                                   
                        },
                        204: function() { 
                                aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("O CPF/CNPJ inválido ou formato incorreto."); 
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('fieldWithErrors');
                        },
                        404: function() { 
                                aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("Serviço WS para acessos externos não encontrado."); 
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('fieldWithErrors');
                        },
                        406: function() { 
                                aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("A consulta processual não retornou dados do CPF/CNPJ da parte informada."); 
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('fieldWithErrors');
                        },
                        500: function() { 
                                aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("Serviço externo indisponível. Tente novamente mais tarde."); 
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('fieldWithErrors');
                        },
                        503: function() { 
                                aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("Serviço externo indisponível. Tente novamente mais tarde."); 
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('fieldWithErrors');
                        },
                        666: function(xhr) { 
                               console.log(xhr.responseText);
                              $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldSuccess');
                              $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldWithErrors');
                              $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('invisible');	
                              $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('fieldWithErrors');
                              aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj(xhr.responseText);                        
                        }
                },

                
                        success: function(data, textStatus, jqXHR) {
                                $("#solicitacaoTransiente_beneficiario_pessoa_nome").val(data);
                                
                },
                

                complete: function() {
                    $("#tribunais_ajaxGif_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button").hide();
                    $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button").removeAttr("disabled");

                    
                        $("#solicitacaoTransiente_beneficiario_pessoa_nome\\.errors").hide();
                    

                    $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").trigger("eventFinalizarRequisicaoAjax");
                }
        });
	
	return true;
}

function aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj(validacaoMsg) {
	if(validacaoMsg != ""){
		$("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('invisible');	
	}else{
		$("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('invisible');
	}
    $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").html(validacaoMsg);
    
    
	    if(validacaoMsg == "") {
			$("#solicitacaoTransiente_beneficiario_pessoa_nome").attr("readonly", "readonly");
	    } else {
	    			
	    }
    
    
//    if(document.getElementById('cb_tipoFinalidade') != null){
//        var tp_finalidade = document.getElementById('cb_tipoFinalidade').value;
//        console.log("finalidade <:> " + tp_finalidade );
//        if(tp_finalidade === "PIX"){
//           //  this.montaComboTitularConta();
//            // window.addEventListener("load", function(){
//                    montaComboTitularConta(); 
//            //    });
//         }
//     }  
}



</script>
	</td>
</tr>

<tr id="linha_beneficiario_nome" class="finalidade_credito_outros_bancos" style="opacity: 1; display: none;">
    <td id="tituloBeneficiario_nome" class="titulo">
            
                    
                          Nome Beneficiário
                    
                    
            
    </td>
    <td>
        <input id="solicitacaoTransiente_beneficiario_pessoa_nome" name="solicitacaoTransiente.beneficiario.pessoa.nome" readonly="readonly" type="text" value="" size="45" maxlength="100">
        
    </td>
</tr>


    
    
   
         
     
    <tr id="linhaBeneficiarioTitularConta">
        <td class="titulo">
            Beneficiário/Procurador/Representante é igual ao titular da conta?*
            









<span title="Sim: validar o CPF/CNPJ do beneficiário do resgate X Conta Destino.

Não: não será feito a validação podendo o recurso ser enviado para outra pessoa que não seja o Beneficiário." class="bt-acao-ajuda"> </span>
        </td>
        <td>
            <input id="rb_beneficiarioTitularContaTrue" name="finalidadeCreditoOutrosBancos.indicadorBeneficiarioTitularConta" onload="beneficiarioEhTitularConta()" onchange=" carregarCpfCnpjNomeBeneficiarioTitularConta();verificarMostrarTitular();" type="radio" value="S"> 
            Sim
            <input id="rb_beneficiarioTitularContaFalse" name="finalidadeCreditoOutrosBancos.indicadorBeneficiarioTitularConta" onclick="verificaStatus(this.value)" onchange="verificarMostrarTitular();" type="radio" value="N"> 
            Não
            
        </td>
    </tr>



    
    <tr id="selecao_tipoBeneficiario" class="finalidade_credito_outros_bancos">
            <td class="titulo">Procurador / Representante Legal</td>
            <td>
                    <input id="rb_procurador" name="representantes" type="checkbox" value="PROCURADOR"><input type="hidden" name="_representantes" value="on">
                    Procurador
                    <input id="rb_representanteLegal" name="representantes" type="checkbox" value="REPRESENTANTE_LEGAL"><input type="hidden" name="_representantes" value="on">
                    Representante Legal

                    
            </td>
    </tr>

    <tr id="linha_procurador_cpfCnpj" class="finalidade_credito_outros_bancos" style="">
                <td class="titulo">
                    CPF/CNPJ Procurador*
                    









<span title="Preencha o CPF ou CNPJ sem formatação." class="bt-acao-ajuda"> </span>
                </td>
                <td>
                        

































        
        
<div style="float:left">
	<input id="solicitacaoTransiente_procurador_cpfCnpj" name="solicitacaoTransiente.procurador.cpfCnpj" onkeydown="Mascara(this,CpfCnpjContagem);" onblur="montaComboTitularContaPIX()" onchange="Mascara(this,CpfCnpjContagem);" type="text" value="" size="40" maxlength="18">
	





















<input type="button" id="solicitacaoTransiente_procurador_cpfCnpj_button" class="botaoAtualizar invisivel" value="Validar" onclick="executarAcao_solicitacaoTransiente_procurador_cpfCnpj_button()">

<script type="text/javascript">

	function executarAcao_solicitacaoTransiente_procurador_cpfCnpj_button(){
				
                
	            var retorno = true;

                
                        retorno = validaCpfCnpj_solicitacaoTransiente_procurador_cpfCnpj();
                
        
                
                        
                if(retorno) {
                        
                }
	}
</script>

	<span id="span_solicitacaoTransiente_procurador_cpfCnpj" class="fieldWithErrors invisible"></span>
	
        <br>
        <label id="lb_msg_cpf_cnpj_quantidade_digitos" style="color:#555555; font-size:10px;">(Informe 11 (onze) digitos para CPF ou 14 (quatorze) para CNPJ)</label>
</div>
<script type="text/javascript">
function validaCpfCnpj_solicitacaoTransiente_procurador_cpfCnpj() {
        $("#solicitacaoTransiente\\.procurador\\.nome").val("");
	var cpfCnpj = Integer($("#solicitacaoTransiente_procurador_cpfCnpj").val());
	cpfCnpj = cpfCnpj.replace(/[-./]/g, '');
	if(cpfCnpj == "") {
		
		    $("#solicitacaoTransiente\\.procurador\\.nome").val("");
		    
		    
		    
		    $("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('invisible');
		    $("#tribunais_ajaxGif_solicitacaoTransiente_procurador_cpfCnpj_button").hide();
		    $("#solicitacaoTransiente_procurador_cpfCnpj_button").removeAttr("disabled");
		
		return true;
	}

	if("CPFCNPJ" === 'CPFCNPJ'){

		if($("#solicitacaoTransiente_procurador_cpfCnpj").val().length!=14 && $("#solicitacaoTransiente_procurador_cpfCnpj").val().length!=18){
		            aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	if("CPFCNPJ" === 'CPF'){

		if($("#solicitacaoTransiente_procurador_cpfCnpj").val().length!=14){
		            aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	if("CPFCNPJ" === 'CNPJ'){

		if($("#solicitacaoTransiente_procurador_cpfCnpj").val().length!=18){
		            aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	
	$("#tribunais_ajaxGif_solicitacaoTransiente_procurador_cpfCnpj_button").show();
		
	// realiza chamada WS
	$("#solicitacaoTransiente_procurador_cpfCnpj").trigger("eventIniciarRequisicaoAjax");
        
        
        //validar cpfcnpj nas partes do processo e no bb ou somento no bb
        if(false){
                var opt = $("#cb_tipoBeneficiario > option:checked");
                var tipo = opt.attr('tipo');
                var url = "/portaltrtsp/pages/processo/tribunal/"+$("#numeroProcesso").val()+"/cpfcnpj/"+cpfCnpj+"/"+tipo+"/validar.json";
        }else{      
                var url = "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validarModulo.json";
                
                        url = "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validar.json";
                
        }
        
        var ajaxReq = $.ajax(url, {
                dataType: "text",

                statusCode: {
                        200: function() { 
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldWithErrors');
                                aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("");
                                   
                        },
                        204: function() { 
                                aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("O CPF/CNPJ inválido ou formato incorreto."); 
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('fieldWithErrors');
                        },
                        404: function() { 
                                aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("Serviço WS para acessos externos não encontrado."); 
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('fieldWithErrors');
                        },
                        406: function() { 
                                aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("A consulta processual não retornou dados do CPF/CNPJ da parte informada."); 
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('fieldWithErrors');
                        },
                        500: function() { 
                                aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("Serviço externo indisponível. Tente novamente mais tarde."); 
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('fieldWithErrors');
                        },
                        503: function() { 
                                aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("Serviço externo indisponível. Tente novamente mais tarde."); 
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('fieldWithErrors');
                        },
                        666: function(xhr) { 
                               console.log(xhr.responseText);
                              $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldSuccess');
                              $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldWithErrors');
                              $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('invisible');	
                              $("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('fieldWithErrors');
                              aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj(xhr.responseText);                        
                        }
                },

                
                        success: function(data, textStatus, jqXHR) {
                                $("#solicitacaoTransiente\\.procurador\\.nome").val(data);
                                
                },
                

                complete: function() {
                    $("#tribunais_ajaxGif_solicitacaoTransiente_procurador_cpfCnpj_button").hide();
                    $("#solicitacaoTransiente_procurador_cpfCnpj_button").removeAttr("disabled");

                    
                        $("#solicitacaoTransiente\\.procurador\\.nome\\.errors").hide();
                    

                    $("#solicitacaoTransiente_procurador_cpfCnpj").trigger("eventFinalizarRequisicaoAjax");
                }
        });
	
	return true;
}

function aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj(validacaoMsg) {
	if(validacaoMsg != ""){
		$("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('invisible');	
	}else{
		$("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('invisible');
	}
    $("#span_solicitacaoTransiente_procurador_cpfCnpj").html(validacaoMsg);
    
    
	    if(validacaoMsg == "") {
			$("#solicitacaoTransiente\\.procurador\\.nome").attr("readonly", "readonly");
	    } else {
	    			
	    }
    
    
//    if(document.getElementById('cb_tipoFinalidade') != null){
//        var tp_finalidade = document.getElementById('cb_tipoFinalidade').value;
//        console.log("finalidade <:> " + tp_finalidade );
//        if(tp_finalidade === "PIX"){
//           //  this.montaComboTitularConta();
//            // window.addEventListener("load", function(){
//                    montaComboTitularConta(); 
//            //    });
//         }
//     }  
}



</script>
                </td>
        </tr>
        <tr id="linha_procurador_nome" class="finalidade_credito_outros_bancos" style="">
                <td class="titulo">Nome Procurador*</td>
                <td>
                        <input id="solicitacaoTransiente.procurador.nome" name="solicitacaoTransiente.procurador.nome" onchange="carregarListaPix()" type="text" value="" size="45" maxlength="100">
                        
                </td>
        </tr>
        <tr id="linha_procurador_registroOAB" class="finalidade_credito_outros_bancos" style="">
                <td class="titulo">N° Registro OAB*</td>
                <td>
                        <input id="solicitacaoTransiente.numeroRegistroOab" name="solicitacaoTransiente.numeroRegistroOab" type="text" value="" size="10" maxlength="10">
                        
                </td>
        </tr>
        <tr id="linha_procurador_ufOAB" class="finalidade_credito_outros_bancos" style="">
                <td class="titulo">
                        UF OAB*
                </td>   
                <td>
                        <select id="cb_estados" name="solicitacaoTransiente.estado" style="min-width: 150px; display: none;">
                                <option value="" selected="selected">Selecione...</option>
                                <option value="AC">AC</option><option value="AL">AL</option><option value="AM">AM</option><option value="AP">AP</option><option value="BA">BA</option><option value="CE">CE</option><option value="DF">DF</option><option value="ES">ES</option><option value="GO">GO</option><option value="MA">MA</option><option value="MG">MG</option><option value="MS">MS</option><option value="MT">MT</option><option value="PA">PA</option><option value="PB">PB</option><option value="PE">PE</option><option value="PI">PI</option><option value="PR">PR</option><option value="RJ">RJ</option><option value="RN">RN</option><option value="RO">RO</option><option value="RR">RR</option><option value="RS">RS</option><option value="SC">SC</option><option value="SE">SE</option><option value="SP">SP</option><option value="TO">TO</option>
                        </select><div class="chosen-container chosen-container-single" style="width: 150px;" title="" id="cb_estados_chosen"><a class="chosen-single" tabindex="-1"><span>SP</span><div><b></b></div></a><div class="chosen-drop"><div class="chosen-search"><input type="text" autocomplete="off"></div><ul class="chosen-results"><li class="active-result result-selected" style="" data-option-array-index="26"><em>SP</em></li></ul></div></div>
                        
                </td>
        </tr>
        <tr id="linha_procurador_tipoOAB" class="finalidade_credito_outros_bancos" style="">
                <td class="titulo">
                        Tipo OAB*
                </td>
                <td>
                        <input id="solicitacaoTransiente.tipoRegistroOab" name="solicitacaoTransiente.tipoRegistroOab" type="text" value="" size="20" maxlength="20">
                        

                </td>
        </tr>

    <tr id="linha_representanteLegal_cpfCnpj" class="finalidade_credito_outros_bancos" style="display: none !important;">
                <td class="titulo">
                    CPF/CNPJ Representante Legal*
                    









<span title="Preencha o CPF ou CNPJ sem formatação." class="bt-acao-ajuda"> </span>
                </td>
                <td>
                        

































        
        
<div style="float:left">
	<input id="solicitacaoTransiente_representanteLegal_cpfCnpj" name="solicitacaoTransiente.representanteLegal.cpfCnpj" onkeydown="Mascara(this,CpfCnpjContagem);" onblur="montaComboTitularContaPIX()" onchange="Mascara(this,CpfCnpjContagem);" type="text" value="" size="40" maxlength="18">
	





















<input type="button" id="solicitacaoTransiente_representanteLegal_cpfCnpj_button" class="botaoAtualizar invisivel" value="Validar" onclick="executarAcao_solicitacaoTransiente_representanteLegal_cpfCnpj_button()">

<script type="text/javascript">

	function executarAcao_solicitacaoTransiente_representanteLegal_cpfCnpj_button(){
				
                
	            var retorno = true;

                
                        retorno = validaCpfCnpj_solicitacaoTransiente_representanteLegal_cpfCnpj();
                
        
                
                        
                if(retorno) {
                        
                }
	}
</script>

	<span id="span_solicitacaoTransiente_representanteLegal_cpfCnpj" class="fieldWithErrors invisible"></span>
	
        <br>
        <label id="lb_msg_cpf_cnpj_quantidade_digitos" style="color:#555555; font-size:10px;">(Informe 11 (onze) digitos para CPF ou 14 (quatorze) para CNPJ)</label>
</div>
<script type="text/javascript">
function validaCpfCnpj_solicitacaoTransiente_representanteLegal_cpfCnpj() {
        $("#solicitacaoTransiente\\.representanteLegal\\.nome").val("");
	var cpfCnpj = Integer($("#solicitacaoTransiente_representanteLegal_cpfCnpj").val());
	cpfCnpj = cpfCnpj.replace(/[-./]/g, '');
	if(cpfCnpj == "") {
		
		    $("#solicitacaoTransiente\\.representanteLegal\\.nome").val("");
		    
		    
		    
		    $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('invisible');
		    $("#tribunais_ajaxGif_solicitacaoTransiente_representanteLegal_cpfCnpj_button").hide();
		    $("#solicitacaoTransiente_representanteLegal_cpfCnpj_button").removeAttr("disabled");
		
		return true;
	}

	if("CPFCNPJ" === 'CPFCNPJ'){

		if($("#solicitacaoTransiente_representanteLegal_cpfCnpj").val().length!=14 && $("#solicitacaoTransiente_representanteLegal_cpfCnpj").val().length!=18){
		            aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	if("CPFCNPJ" === 'CPF'){

		if($("#solicitacaoTransiente_representanteLegal_cpfCnpj").val().length!=14){
		            aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	if("CPFCNPJ" === 'CNPJ'){

		if($("#solicitacaoTransiente_representanteLegal_cpfCnpj").val().length!=18){
		            aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	
	$("#tribunais_ajaxGif_solicitacaoTransiente_representanteLegal_cpfCnpj_button").show();
		
	// realiza chamada WS
	$("#solicitacaoTransiente_representanteLegal_cpfCnpj").trigger("eventIniciarRequisicaoAjax");
        
        
        //validar cpfcnpj nas partes do processo e no bb ou somento no bb
        if(false){
                var opt = $("#cb_tipoBeneficiario > option:checked");
                var tipo = opt.attr('tipo');
                var url = "/portaltrtsp/pages/processo/tribunal/"+$("#numeroProcesso").val()+"/cpfcnpj/"+cpfCnpj+"/"+tipo+"/validar.json";
        }else{      
                var url = "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validarModulo.json";
                
                        url = "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validar.json";
                
        }
        
        var ajaxReq = $.ajax(url, {
                dataType: "text",

                statusCode: {
                        200: function() { 
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldWithErrors');
                                aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("");
                                   
                        },
                        204: function() { 
                                aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("O CPF/CNPJ inválido ou formato incorreto."); 
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('fieldWithErrors');
                        },
                        404: function() { 
                                aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("Serviço WS para acessos externos não encontrado."); 
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('fieldWithErrors');
                        },
                        406: function() { 
                                aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("A consulta processual não retornou dados do CPF/CNPJ da parte informada."); 
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('fieldWithErrors');
                        },
                        500: function() { 
                                aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("Serviço externo indisponível. Tente novamente mais tarde."); 
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('fieldWithErrors');
                        },
                        503: function() { 
                                aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("Serviço externo indisponível. Tente novamente mais tarde."); 
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('fieldWithErrors');
                        },
                        666: function(xhr) { 
                               console.log(xhr.responseText);
                              $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldSuccess');
                              $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldWithErrors');
                              $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('invisible');	
                              $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('fieldWithErrors');
                              aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj(xhr.responseText);                        
                        }
                },

                
                        success: function(data, textStatus, jqXHR) {
                                $("#solicitacaoTransiente\\.representanteLegal\\.nome").val(data);
                                
                },
                

                complete: function() {
                    $("#tribunais_ajaxGif_solicitacaoTransiente_representanteLegal_cpfCnpj_button").hide();
                    $("#solicitacaoTransiente_representanteLegal_cpfCnpj_button").removeAttr("disabled");

                    
                        $("#solicitacaoTransiente\\.representanteLegal\\.nome\\.errors").hide();
                    

                    $("#solicitacaoTransiente_representanteLegal_cpfCnpj").trigger("eventFinalizarRequisicaoAjax");
                }
        });
	
	return true;
}

function aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj(validacaoMsg) {
	if(validacaoMsg != ""){
		$("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('invisible');	
	}else{
		$("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('invisible');
	}
    $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").html(validacaoMsg);
    
    
	    if(validacaoMsg == "") {
			$("#solicitacaoTransiente\\.representanteLegal\\.nome").attr("readonly", "readonly");
	    } else {
	    			
	    }
    
    
//    if(document.getElementById('cb_tipoFinalidade') != null){
//        var tp_finalidade = document.getElementById('cb_tipoFinalidade').value;
//        console.log("finalidade <:> " + tp_finalidade );
//        if(tp_finalidade === "PIX"){
//           //  this.montaComboTitularConta();
//            // window.addEventListener("load", function(){
//                    montaComboTitularConta(); 
//            //    });
//         }
//     }  
}



</script>
                </td>
        </tr>
        <tr id="linha_representanteLegal_nome" class="finalidade_credito_outros_bancos" style="display: none !important;">
                <td class="titulo">Nome Representante Legal*</td>
                <td>
                        <input id="solicitacaoTransiente.representanteLegal.nome" name="solicitacaoTransiente.representanteLegal.nome" onchange="carregarListaPix()" type="text" value="" size="45" maxlength="100">
                        
                </td>
        </tr>

    <tr id="linhaFolhaProcuracao" class="finalidade_credito_outros_bancos" style="opacity: 1; display: table-row;">
            <td class="titulo">
                    Folha da Procuração
            </td>
            <td>
                    <input id="solicitacaoTransiente.folhaProcuracao" name="solicitacaoTransiente.folhaProcuracao" type="text" value="">
                    
            </td>
    </tr>

    
<script type="text/javascript">
    
    function carregarListaPix(){
        var combo = document.getElementById('pixDi1namico');

        if (combo !== null && combo !== undefined){ 
            for (a in combo.options) { combo.options.remove(a); }
        }

        var podeSelecionar = document.getElementById('rb_beneficiarioTitularContaFalse').checked;

        if(!podeSelecionar){
            $("#linhaChavePixDinamico").fadeOut();
            $("#linhaChavePixCpfCnpjBeneficiario").fadeIn();
            
            var cpfCnpj = $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val();
            var nome = $("#solicitacaoTransiente_beneficiario_pessoa_nome").val();

            preecherCamposCpfCnpjNomeFinalidadePIX(cpfCnpj, nome);
            
            return;
                
        }
        
        $("#linhaChavePixDinamico").fadeIn();
        $("#linhaChavePixCpfCnpjBeneficiario").fadeOut();

        var beneficiario = document.getElementById('solicitacaoTransiente_beneficiario_pessoa_cpfCnpj').value;

        var procurador = document.getElementById('solicitacaoTransiente_procurador_cpfCnpj').value;

        var representante = document.getElementById('solicitacaoTransiente_representanteLegal_cpfCnpj').value;



        combo.appendChild(new Option('Selecione','selecione'));
        
        if(beneficiario !== null && beneficiario.trim().length !== 0){
            combo.appendChild(new Option(beneficiario,beneficiario));
        }

        if(procurador !== null && procurador.trim().length !== 0){
            combo.appendChild(new Option(procurador,procurador));
        }
        
        if(representante !== null && representante.trim().length !== 0){
            combo.appendChild(new Option(representante,representante));
        }
        
        
        combo.addEventListener('change', function handle(event){
            var selectElement = event.target;
            var value = selectElement.value;    
            
            
            var value2 = combo.options[combo.selectedIndex].value;
            var text2 = combo.options[combo.selectedIndex].text;
            
            preecherCamposCpfCnpjNomeFinalidadePIX(value2, text2);
            
        });
    }
    
        var finalidade = document.getElementById('cb_tipoFinalidade').value;
        
        if (finalidade === "CREDITO_CONTA_BB" || finalidade === "CREDITO_CONTA_OUTRO_BANCO" || finalidade === "PIX") {
            document.getElementById('rb_beneficiarioTitularContaFalse').addEventListener('click', function(e){  
                limparCpfCnpjNomeFinalidade();
            });

            document.getElementById('rb_beneficiarioTitularContaTrue').addEventListener('click', function(e){  
                carregarCpfCnpjNomeBeneficiarioTitularConta(finalidade);
            });
        }
        
        $(document).ready(function(){
            var mensagemErro = document.getElementById('msgException');
            if (mensagemErro === undefined || mensagemErro === null) {
                $("#rb_representanteLegal").prop("checked", false);
                $("#rb_procurador").prop("checked", false);
                limparCamposProcurador();
                limparCamposRepresentanteLegal();
                ocultarConteudoBeneficiario();
                ocultarConteudoProcurador();
                ocultarConteudoRepresentanteLegal();
                verificarInclusaoCampoFolhaProcuracao();
                verificarFinalidadeCredito();
            }
            setTimeout(()=> {
                carregarTipoBeneficiario();
                reloadTipoBeneficiario();
                criarChanges();
                reloadRadioRepresentacao();
                $("#cb_tipoBeneficiario_chosen").css("width","203");
                $("#cb_tipoBeneficiario").trigger("chosen:updated");
                removerDuplicados();
                verificarMostrarTitular();
            }, 500);
        });
        
        function verificarMostrarTitular() {
            if($("#cb_tipoFinalidade").val() === "CREDITO_CONTA_OUTRO_BANCO"){
                var podeSelecionar = document.getElementById('rb_beneficiarioTitularContaTrue');
                if (podeSelecionar !== null && podeSelecionar !== undefined && podeSelecionar.checked) {
                    $("#cpf_cnpj_titular_finalidade_credito_outros_bancos").fadeOut();
                    $("#nome_titular_finalidade_credito_outros_bancos").fadeOut();
                    var linhaPix = document.getElementById("linhaChavePixCpfCnpjBeneficiario");
                    linhaPix.style.opacity = '1';
                    $("#linhaChavePixCpfCnpjBeneficiario").fadeIn();
                } else {
                    $("#linhaChavePixCpfCnpjBeneficiario").fadeOut();
                    $("#cpf_cnpj_titular_finalidade_credito_outros_bancos").fadeIn();
                    $("#nome_titular_finalidade_credito_outros_bancos").fadeIn();
                } 
            }
        }
        
        function verificarFinalidadeCredito() {
            if ($("#cb_tipoFinalidade").val() === "CREDITO_CONTA_BB" || $("#cb_tipoFinalidade").val() === "CREDITO_CONTA_OUTRO_BANCO" || $("#cb_tipoFinalidade").val() === "PIX") {
                $("#rb_beneficiarioTitularContaTrue").prop("checked", true);
            } else {
                $("#rb_beneficiarioTitularContaTrue").prop("checked", false);
            }
        }
        
        function beneficiarioEhTitularConta(){
            if ($("#cb_tipoFinalidade").val() === "CREDITO_CONTA_BB" || $("#cb_tipoFinalidade").val() === "CREDITO_CONTA_OUTRO_BANCO" || $("#cb_tipoFinalidade").val() === "PIX") {
                $("#rb_beneficiarioTitularContaTrue").prop("checked", true);
            } else {
                $("#rb_beneficiarioTitularContaTrue").prop("checked", false);
            }
        }
        
        function carregarCpfCnpjNomeBeneficiarioTitularConta() {
            var finalidade = document.getElementById('cb_tipoFinalidade').value;
            var tipoBeneficiario = document.getElementById('cb_tipoBeneficiario').value;

            if (finalidade === "PIX" && tipoBeneficiario !== "") {

                var cpfCnpj = "";
                var nome = "";
                var beneficiarioEhIgualTitularConta = $("#rb_beneficiarioTitularContaTrue").is(':checked');

                if (beneficiarioSelecionadoDoCombo && beneficiarioEhIgualTitularConta) {

                    cpfCnpj = recuperarCpfCnpjBeneficiarioSelecionadoComMascara();
                    nome = $("#comboBeneficiario option:selected").text();
                }

                if (beneficiarioDigitadoManualmente && beneficiarioEhIgualTitularConta) {

                    cpfCnpj = $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val();
                    nome = $("#solicitacaoTransiente_beneficiario_pessoa_nome").val();
                }

                if (cpfCnpj !== "" && nome !== "") {
                    preecherCamposCpfCnpjNomeFinalidadePIX(cpfCnpj, nome);
                }
            } else {
                //console.log("Null" );
            }

        }
        
        function preencherCpfNomeQuandoTerceiros(name, cpfCnpj){
            var finalidade = document.getElementById('cb_tipoFinalidade').value;
            var beneficiarioEhIgualTitularConta = $("#rb_beneficiarioTitularContaTrue").is(':checked');
            if (finalidade === "CREDITO_CONTA_OUTRO_BANCO" && beneficiarioEhIgualTitularConta) {
                $("#finalidadeCreditoOutrosBancos_titular_nome").val(name);
                $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").val(cpfCnpj);
            }
        }
        
        function recuperarCpfCnpjBeneficiarioSelecionadoComMascara() {
            var cpfCnpj = "";
            if ($("#comboBeneficiario").val() !== "0") {
                cpfCnpj = $("#comboBeneficiario").find(':selected').attr('cpf');//01234567890 00000000000191
                cpfCnpj = mascaraCpfCnpj(cpfCnpj);
            }
            return cpfCnpj;
        }
        
        function preecherCamposCpfCnpjNomeFinalidade(cpfCnpj, nome) {
            $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").val(cpfCnpj);
            $("#finalidadeCreditoOutrosBancos_titular_nome").val(nome);
            $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").attr("readonly", "true");
            $("#finalidadeCreditoOutrosBancos_titular_nome").attr("readonly", "true");
        }
        
        //PIX
          function preecherCamposCpfCnpjNomeFinalidadePIX(cpfCnpj, nome) {
            console.log("cpf: "+$("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val());
            console.log("nome: "+$("#solicitacaoTransiente_beneficiario_pessoa_nome").val());
            $("#finalidadePIX_titular_cpfCnpj").val(cpfCnpj);
            $("#finalidadePIX_titular_nome").val(nome);
            $("#finalidadePIX_titular_nome").attr("readonly", "true");
            
            
          
            
            
        }
        
        function mascaraCpfCnpj (cpfCnpj) {
            if (cpfCnpj !== null && cpfCnpj !== undefined) {
                if (cpfCnpj.length == 11) {
                    var g1 = cpfCnpj.substring(0, 3);
                    var g2 = cpfCnpj.substring(3, 6);
                    var g3 = cpfCnpj.substring(6, 9);
                    var g4 = cpfCnpj.substring(9, 11);
                    return g1 + "." + g2 + "." + g3 + "-" + g4;
                }
                if (cpfCnpj.length == 14) {
                    var g1 = cpfCnpj.substring(0, 2);
                    var g2 = cpfCnpj.substring(2, 5);
                    var g3 = cpfCnpj.substring(5, 8);
                    var g4 = cpfCnpj.substring(8, 12);
                    var g5 = cpfCnpj.substring(12, 14);
                    return g1 + "." + g2 + "." + g3 + "/" + g4 + "-" + g5;
                }
            }
            return cpfCnpj;
        }
        
        function limparBeneficiario() {
        	var spanAvisoCPF = $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj");
        	if (spanAvisoCPF!=undefined) spanAvisoCPF.fadeOut();
            //esconderOuApresentarLinhaBeneficiarioCpfCnpj();
            limparCpfCnpjNomeSolicitacao();
            limparCpfCnpjNomeFinalidade();
            limpaElementosHiddenBeneficiario();
        }
        
        function verificarBeneficiarioSelecionado() {
           // debugger;
            if ($("#comboBeneficiario").val() !== "0") {
                $("#beneficiario").val($("#beneficiarioTransiente").val());
                preencherCampoCpfCnpj(); 
                carregarCpfCnpjNomeBeneficiarioTitularConta();
            } else {
                limparCpfCnpjNomeSolicitacao();
                limparCpfCnpjNomeFinalidade();
                limparCampoCpfCnpj();
            }
            montaComboTitularContaPIX();
        }
        

        function limparCampoCpfCnpj() {
            $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val("");
            $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").prop("disabled", false);
        }
        
        function esconderOuApresentarLinhaBeneficiarioCpfCnpj() {               
            if (isTipoBeneficiarioSelecionadoSomenteSelecao()) {
                $("#linha_beneficiario_cpfCnpj").fadeOut();
                $("#linha_beneficiario_nome").fadeOut();
                $('#lb_msg_cpf_cnpj_quantidade_digitos').css('display', 'none');
            } else {
                $("#linha_beneficiario_cpfCnpj").fadeIn();
                $("#linha_beneficiario_nome").fadeIn();
                $('#lb_msg_cpf_cnpj_quantidade_digitos').css('display', 'block');
            }
        }
               
        function isTipoBeneficiarioSelecionadoSomenteSelecao() {
              //  var tiposBeneficiariosSomenteSelecao = ['1', '5'];
            var tiposBeneficiariosSomenteSelecao = ['1', '5', '9', '10'];
            var tipoBeneficiarioSelecionado = $("#cb_tipoBeneficiario").val();
            return tiposBeneficiariosSomenteSelecao.includes(tipoBeneficiarioSelecionado);
        }
        
        function preencherCampoCpfCnpj() {
            var cpfCnpj = mascaraCpfCnpj($("#comboBeneficiario").val());
            $("#linha_beneficiario_cpfCnpj").fadeIn();
            
			// Pra qualquer das situaï¿½ï¿½es, o CPF/CNPJ deve ser desabilitado. 
          //  $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").prop("disabled", true);
			
            if (cpfCnpj) {
                $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val(cpfCnpj);
                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").fadeOut();
                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").text("");
            } else {
                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").fadeIn();
                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").text("CPF/CNPJ não informado. Retifique o cadastro da parte no processo");
            }
        }
        
        function limparCpfCnpjNomeSolicitacao() {
                $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val("");
                $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeAttr("readonly");
                $("#solicitacaoTransiente_beneficiario_pessoa_nome").val("");
                $("#solicitacaoTransiente_beneficiario_pessoa_nome").attr("readonly", "false");
        }
        
        function limparCpfCnpjNomeFinalidade() {
                $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").val("");
                $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").removeAttr("readonly");
                $("#finalidadeCreditoOutrosBancos_titular_nome").val("");
                $("#finalidadeCreditoOutrosBancos_titular_nome").attr("readonly", "true");
        }
        
        function limparCpfCnpjNomeFinalidadePIX() {
                $("#finalidadePIX_titular_cpfCnpj").val("");
                $("#finalidadePIX_titular_cpfCnpj").removeAttr("readonly");
                $("#finalidadePIX_titular_nome").val("");
                $("#finalidadePIX_titular_nome").attr("readonly", "true");
        }
        
        
        function byPassCpfCnpjBeneficiarioConta() {
            $("#solicitacaoTransiente_beneficiario_pessoa_nome").trigger("onblur");
            montaComboTitularContaPIX();
        }

        function cbTipoBeneficiarioChange(){
            limparBeneficiario();
            addChange();
        }
        
        function addChange() {
            var eventos = "validaCpfCnpj_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj();";//$("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").attr("onblur");
            eventos += "byPassCpfCnpjBeneficiarioConta();";
            $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").attr("onblur", eventos);
            $("#solicitacaoTransiente_procurador_cpfCnpj").attr("onblur", "montaComboTitularContaPIX()");
            $("#solicitacaoTransiente_representanteLegal_cpfCnpj").attr("onblur", "montaComboTitularContaPIX()");
        }
        
        function montaComboTitularContaPIX(){
            var cpf_beneficiario = $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val();
            var nm_beneficiario  = "";
            var beneficiario_selecionado = $('#comboBeneficiario').find(":selected").val();

            if(beneficiario_selecionado !== '0' && beneficiario_selecionado !== undefined){
                nm_beneficiario = $('#comboBeneficiario').find(":selected").text();
            }else{
                if(cpf_beneficiario !== undefined && cpf_beneficiario !== null && cpf_beneficiario.length > 0){
                    nm_beneficiario = recuperaNomePorCpfCnpj(cpf_beneficiario); 
                }
            }

            var select = document.querySelector('#select_titular');            
            if(select !== null){
                var cont = select.length;
                   while(select.length > 0){
                       console.log(select.length);
                          select.remove(cont--);
                   }
                select.options[select.options.length] = new Option("SELECIONE...",  "");

                //#Beneficiario    
                if(cpf_beneficiario !== undefined && cpf_beneficiario !== null && cpf_beneficiario.length > 0){
                    select.options[select.options.length] = new Option(cpf_beneficiario+" -"+ nm_beneficiario, cpf_beneficiario+" - "+ nm_beneficiario);
                 }
             }

            //#Procurador
            var cpf_procurador = $("#solicitacaoTransiente_procurador_cpfCnpj").val();
            var nm_procurador  =""; 

            if(cpf_procurador !== undefined && cpf_procurador !== null && cpf_procurador.length > 13){
                nm_procurador = recuperaNomePorCpfCnpj(cpf_procurador); 
                $("#solicitacaoTransiente\\.procurador\\.nome").val(nm_procurador);
                if(select !== null){
                    select.options[select.options.length] = new Option(cpf_procurador+" -"+ nm_procurador, cpf_procurador+" - "+ nm_procurador);
                }
             }

            //#Representante Legal
            var cpf_representante = $("#solicitacaoTransiente_representanteLegal_cpfCnpj").val();
            var nm_representante  =""; 

            if(cpf_representante !== undefined && cpf_representante !== null && cpf_representante.length > 13){
                nm_representante = recuperaNomePorCpfCnpj(cpf_representante); 
                $("#solicitacaoTransiente\\.representanteLegal\\.nome").val(nm_representante);
                if(select !== null){
                    select.options[select.options.length] = new Option(cpf_representante+" -"+ nm_representante, cpf_representante+" - "+ nm_representante);
                }
             }  
            preecherCamposTransicaoCpfCnpjNomeFinalidadePIX();  
          }
          
          function preecherCamposTransicaoCpfCnpjNomeFinalidadePIX() {
            var valorComboChavePix = $("#select_titular").val();
            if(valorComboChavePix !== undefined){
                var arrayAtributos =  valorComboChavePix.split(" - "); 

                console.log("nome: "+arrayAtributos[1]);
                $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").val(arrayAtributos[0]);
                $("#finalidadeCreditoOutrosBancos_titular_nome").val(arrayAtributos[1]);
            }
        }

        function recuperaNomePorCpfCnpj(cpfCnpj){
            var nomeUserCpf="";
            cpfCnpj = cpfCnpj.replaceAll(".", "").replaceAll("-","").replaceAll("/", "");
            //mostrarTelaCarregando();
            console.log("bloqueio de tela!");
            //const mostrarTelaCarregando = () => $("#bloqueio").addClass("escurecer");
           // const esconderTelaCarregando = () => $("#bloqueio").removeClass("escurecer");
            const retornoComSucesso = (data) => nomeUserCpf = data;

            $.ajax(
                "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validar.json",
                {
                  //  beforeSend: mostrarTelaCarregando,
                    success: retornoComSucesso,
                    dataType: "text",
                    async: false
                }
            )
           // .complete(esconderTelaCarregando);

            return nomeUserCpf;
        }
                
        function exibirLinhaCpfCnpjBeneficiario() {
            if (($("#cb_tipoFinalidade").val() === "CREDITO_CONTA_BB" || $("#cb_tipoFinalidade").val() === "CREDITO_CONTA_OUTRO_BANCO") 
            && $("#comboBeneficiario").val() !== "0") {
                var cpfCnpj = recuperarCpfCnpjBeneficiarioSelecionadoComMascara();
                $("#labelCpfCnpj").val(cpfCnpj);
                $("#linhaCpfCnpjBeneficiario").fadeIn();
            }
        }
        
        function ocultarLinhaCpfCnpjBeneficiario() {
            $("#labelCpfCnpj").val("");
            $("#linhaCpfCnpjBeneficiario").fadeOut();
        }
        
        function reloadTipoBeneficiario(){
             if($("#cb_tipoBeneficiario").val() !== "" ){
                    
                        var valor_tipo_beneficiario = $("#cb_tipoBeneficiario").val();
                        if(valor_tipo_beneficiario === "9" || valor_tipo_beneficiario === "10" || valor_tipo_beneficiario ==="11"){
                                $("#linha_beneficiario_cpfCnpj").fadeIn();
                                $("#linha_beneficiario_nome").fadeIn();
                        }
                        if(valor_tipo_beneficiario === "1" || valor_tipo_beneficiario === "5" || valor_tipo_beneficiario === "1" 
                        || valor_tipo_beneficiario === "3" || valor_tipo_beneficiario === "7" || valor_tipo_beneficiario === ""
                        || valor_tipo_beneficiario === null || valor_tipo_beneficiario === "0"){
                                
                                $("#linha_beneficiario_cpfCnpj").fadeOut();
                                $("#linha_beneficiario_nome").fadeOut();

                        }

                        var opt = $("#cb_tipoBeneficiario > option:checked");
                        var papel = opt.attr('papel');
                        abrirCombo(papel);
                        $("#linhaBeneficiario").css("opacity","1");
                     //   exibirDadosBeneficiario();
             }   
        }
        
        function carregarTipoBeneficiario(){
                $("#cb_tipoBeneficiario").val();
        }
        
        function criarChanges(){
                $("#rb_procurador").change(function(){ 
                        if($(this).is(':checked')){
                                exibirConteudoProcurador();
                        }else{
                                ocultarConteudoProcurador();
                                limparCamposProcurador();
                                $('#cb_estados').prop('selectedIndex',0); 
                                $('#cb_estados').trigger("chosen:updated");
                        }
                        verificarInclusaoCampoFolhaProcuracao();
                });
                
                $("#rb_representanteLegal").change(function(){
                        if($(this).is(':checked')){
                                exibirConteudoRepresentanteLegal();
                        }else{
                                ocultarConteudoRepresentanteLegal();
                                limparCamposRepresentanteLegal();
                        }
                        verificarInclusaoCampoFolhaProcuracao();
                });
                
                function changeTipoBeneficiario(){
                       limpaElementosHiddenBeneficiario()
                        var opt = $("#cb_tipoBeneficiario > option:checked");
                        var tipo = opt.attr('tipo');
                        var papel = opt.attr('papel');
                        
                        switch(tipo){
                                case "AUTOR":
                                        abrirCombo(papel);
                                       // exibirDadosBeneficiario();
                                        break;
                                
                                case "REU":
                                        abrirCombo(papel);
                                      //  exibirDadosBeneficiario();
                                        break;
                                
                                case "ADVOGADO":
                                        abrirCombo(papel);
                                      //  exibirDadosBeneficiario();
                                        break;
                                
                                case "OUTROS":
                                      comLinhaCpfNomeBeneficiario();
                                      
                                      //  exibirDadosBeneficiario();
                                        break;
                                     
                                default: 
//                                        $("#linhaBeneficiario").fadeOut();
                                        //abrirCombo(papel);
                                        //exibirDadosBeneficiario();
                                        resetBeneficiario();
                                        break;
                        }                
                }
                $("#cb_tipoBeneficiario").change(changeTipoBeneficiario);
                $("#comboBeneficiario").change(function(){
                       $("#idBeneficiario").val($("#comboBeneficiario").val());
                       ocultarConteudoBeneficiario();
//                       if($("#comboBeneficiario").val()!=="0"){
//                                ocultarConteudoBeneficiario();
//                       }else{
//                                exibirConteudoBeneficiario();
//                       }
                });
        }
        
        function limparCamposProcurador(){
                $("#solicitacaoTransiente_procurador_cpfCnpj").val("");
                $("#solicitacaoTransiente\\.procurador\\.nome").val("");
                $("#solicitacaoTransiente\\.numeroRegistroOab").val("");
                $("#solicitacaoTransiente\\.tipoRegistroOab").val("");
        }
        
        function limparCamposRepresentanteLegal(){
                $("#solicitacaoTransiente_representanteLegal_cpfCnpj").val("");
                $("#solicitacaoTransiente\\.representanteLegal\\.nome").val("");
        }
        
        function limparCampoFolhaProcuracao(){
                $('#solicitacaoTransiente\\.folhaProcuracao').val('');
        }
    
        function exibirConteudoProcurador(){
                $("#linha_procurador_cpfCnpj").fadeIn();
                $("#linha_procurador_cpfCnpj").css('opacity', '1');
                $("#linha_procurador_nome").fadeIn();
                $("#linha_procurador_nome").css('opacity', '1');
                $("#linha_procurador_registroOAB").fadeIn();
                $("#linha_procurador_registroOAB").css('opacity', '1');
                $("#linha_procurador_ufOAB").fadeIn();
                $("#linha_procurador_ufOAB").css('opacity', '1');
                $("#linha_procurador_tipoOAB").fadeIn();
                $("#linha_procurador_tipoOAB").css('opacity', '1');
                
                $("#cb_estados").chosen();
                $("#cb_estados_chosen").css("width","150");
        }
        
        function exibirConteudoRepresentanteLegal(){
                $("#linha_representanteLegal_cpfCnpj").fadeIn();
                $("#linha_representanteLegal_cpfCnpj").css('opacity', '1');
                $("#linha_representanteLegal_nome").fadeIn();
                $("#linha_representanteLegal_nome").css('opacity', '1');
        }
        
        function exibirDadosBeneficiario(){
            $("#qtdeBeneficiarios").val($('#comboBeneficiario option').size());
            
           // exibirConteudoBeneficiario();
          
                if($("#qtdeBeneficiarios").val() !== null 
                && $("#qtdeBeneficiarios").val() <= 1
                ){
                 $("#linhaBeneficiario").fadeOut();
                }else{
                   $("#linhaBeneficiario").fadeIn();
                   if($("#comboBeneficiario").val()!== null && $("#comboBeneficiario").val()!=="0"){
                           ocultarConteudoBeneficiario();
                   }
                }
                
        }
        
        function exibirConteudoBeneficiario(){
                
                $("#linha_beneficiario_cpfCnpj").fadeIn();
                $("#linha_beneficiario_nome").fadeIn();

        }    
        
        function ocultarConteudoBeneficiario(){
                $("#linha_beneficiario_cpfCnpj").fadeOut();
                $("#linha_beneficiario_nome").fadeOut();
                
                if ($("#cb_tipoBeneficiario").val() === null || $("#cb_tipoBeneficiario").val() === "0") {
                        
                        $('#solicitacaoTransiente_beneficiario_pessoa_nome').val('');
                        $('#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj').val('');
                }
        }
        
        function ocultarConteudoProcurador(){
                $("#linha_procurador_cpfCnpj").fadeOut();
                $("#linha_procurador_nome").fadeOut();
                $("#linha_procurador_registroOAB").fadeOut();
                $("#linha_procurador_ufOAB").fadeOut();
                $("#linha_procurador_tipoOAB").fadeOut();
        }
        
        function ocultarConteudoRepresentanteLegal(){ 
                $("#linha_representanteLegal_cpfCnpj").fadeOut();
                $("#linha_representanteLegal_nome").fadeOut();
        }
        
        function verificarInclusaoCampoFolhaProcuracao(){
                if(!$("#rb_procurador").is(":checked") && !$("#rb_representanteLegal").is(":checked")){
                      $("#linhaFolhaProcuracao").fadeOut();
                      limparCampoFolhaProcuracao();
                }else{
                      $("#linhaFolhaProcuracao").fadeIn();    
                }
                montaComboTitularContaPIX();
        }
        
        function reloadRadioRepresentacao(){
            if($("#rb_procurador").is(":checked")){
                    $("#rb_procurador").trigger("change");
            }
            if($("#rb_representanteLegal").is(":checked")){
                    $("#rb_representanteLegal").trigger("change");
            }
        }
        
        function abrirCombo( papel ){
                $("#linhaBeneficiario").fadeIn();
                carregarComboParte(papel);
        }
        
        function carregarComboParte(papel){ 
                $("#comboBeneficiario").html("<option value='0' selected='selected'>Selecione...</option>");
                $("#comboBeneficiario").trigger("change");  
                var url = "/portaltrtsp/pages/consulta-processual-tribunal-session/"+papel;
                if(url.length > 0){
                        $.ajax({
                                dataType: "json",
                                url: url,
                                async: false,
                                success: function(data){
                                    $("#comboBeneficiario_chosen").hide();
                                        if(data !== 'undefined' && data.length > 0) {
                                                var optionHtml = "";
                                                $.each(data,function(i,element){
                                                    var dadosBeneficiario ="";
                                                        optionHtml += "<option value='"+element.cpfCnpj+"' cpf='"+element.cpfCnpj+"' >"+ element.nome +" </option>";
                                                        dadosBeneficiario ="<input type='hidden' id='"+element.cpfCnpj+"' value='"+element.cpfCnpj+";"+element.nome+";"+element.principal+";"+papel+"'>";
                                                        document.getElementById("camposBeneficiario").innerHTML +=dadosBeneficiario;
   
                                                });
                                                $("#comboBeneficiario").append(optionHtml);
                                                if(data[0].cpfCnpj.length > 0){
                                                    comLinhaComboBeneficiario();
                                                 }else{
                                                    comLinhaCpfNomeBeneficiario();
                                                }  
                                        }else{
                                                limpaElementosHiddenBeneficiario();
                                               // $("#beneficiarioTransiente").val(null); 
                                                comLinhaCpfNomeBeneficiario();
                                             }
                                        if($("#idBeneficiario").val() !== null && $("#idBeneficiario").val()!=="0"){       
                                                $("#comboBeneficiario").val($("#idBeneficiario").val());
                                        }
                                         $("#comboBeneficiario").chosen();
                                        $("#comboBeneficiario").trigger("chosen:updated");
                                        $("#comboBeneficiario_chosen").css("width","450");      
                                }
                        });
                } 
                
        }     

        function setarHiddens(id){
            if (id !== '0' && id !== 'undefined') {
                let valorAgrupado = $("#"+id).val();
                let valordesagrupado = valorAgrupado.split(";");
                preencheElementosHiddenBeneficiario(valordesagrupado[0], //cpfcnpj
                                                    valordesagrupado[1], //nome
                                                    valordesagrupado[2],// principal
                                                    valordesagrupado[3] //papel
                                                    //valordesagrupado[$("#idProcesso").val()] //numeroProcesso
                                                 );
             } 
             
           //document.getElementById("camposBeneficiario").innerHTML = "";
             
        }
        
        function preencheElementosHiddenBeneficiario(cpfCnpj,nome,partePrincipal,papel){

            $("#beneficiario_pessoa_nome").val(nome);
            $("#beneficiario_pessoa_cpfCnpj").val(cpfCnpj);
            $("#beneficiario_parte_principal").val(partePrincipal);
            $("#beneficiario_papel").val(papel);
            $("#beneficiario_processo").val($("#idProcesso").val());
            
               carregarParteSiscondj(cpfCnpj,partePrincipal,papel,$("#idProcesso").val());
              
        }
        
        function limpaElementosHiddenBeneficiario(){

            $("#comboBeneficiario").val('0');
            $("#beneficiario_pessoa_nome").val('');
            $("#beneficiario_pessoa_cpfCnpj").val('');
            $("#beneficiario_parte_principal").val('');
            $("#beneficiario_papel").val('');
            $("#beneficiario_processo").val('');
            $("#beneficiario_id").val('0'); 
            
           // document.getElementById("camposBeneficiario").innerHTML = "";
        }
        
          function carregarParteSiscondj(cpfCnpj,partePrincipal,papel,processo){ 
                var url = "/portaltrtsp/pages/verifica-parte-processo/"+cpfCnpj+"/"+partePrincipal+"/"+papel+"/"+processo;                       
                if(url.length > 0){
                        $.ajax({
                            dataType: "json",
                            url: url,
                            async: false,
                            success: function(data){
                                if(data !== 'undefined') {
                                        $("#beneficiario_id").val(data);
                                }else{
                                        $("#beneficiario_id").val('0'); 
                                    }  
                                }
                        });
                    }   
                }     

        
        
         function comLinhaComboBeneficiario(){
              
            $("#linhaBeneficiario").fadeIn();
            $("#comboBeneficiario_chosen").show();
            ocultarConteudoBeneficiario();
        }
        
        function comLinhaCpfNomeBeneficiario(){
            $("#linhaBeneficiario").fadeOut();
            exibirConteudoBeneficiario(); 
        }
        
        function resetBeneficiario(){
                removerDuplicados();
                $("#linhaBeneficiario").fadeOut();
                 ocultarConteudoBeneficiario();
                 $("#cb_tipoBeneficiario").val("").trigger("chosen:updated"); 
                 //removerDuplicados();
            }
            
            function removerDuplicados() {
                let elementos = document.querySelectorAll("#comboBeneficiario_chosen"); // Seleciona todos os itens duplicados
                if(elementos.length > 0)
                    for (let i = 1; i < elementos.length; i++) { // Mantï¿½m o primeiro, remove os outros
                        elementos[i].remove();
                    }
            }
        
        
          //PIX
    function verificaStatus(valor){
           console.log("verificaStatus(param)");
           var tp_finalidade = document.getElementById('cb_tipoFinalidade').value;
        if(tp_finalidade == "PIX"){
            if(valor==='N'){
                document.getElementById("text_cpfcnpjtitularconta").style.display= '';
                document.getElementById("combo_cpfcnpjtitularconta").style.display= 'none';
                document.getElementById("finalidadePIX_titular_cpfCnpj").value= '';
                 document.getElementById("finalidadePIX_titular_nome").value= '';
            }else{
                document.getElementById("titularesConta").selected="selected";
                document.getElementById("finalidadePIX_titular_nome").value= '';
                document.getElementById("combo_cpfcnpjtitularconta").style.display= '';
                document.getElementById("text_cpfcnpjtitularconta").style.display= 'none';
            }
        }else{
            console.log("No pix");
        }
    }

</script>

<tr class="finalidade_credito_outros_bancos">
	<td class="titulo">Tipo de Crédito*</td>
	<td>
		<select id="cb_tipoCreditoOutrosBancos" name="finalidadeCreditoOutrosBancos.contaBancaria.tipo" style="min-width: 150px; display: none;">
			<option value="">Selecione...</option>
			<option value="CONTA_CORRENTE">Conta Corrente</option><option value="CONTA_POUPANCA">Conta Poupança</option>
		</select><div class="chosen-container chosen-container-single" style="width: 150px;" title="" id="cb_tipoCreditoOutrosBancos_chosen"><a class="chosen-single" tabindex="-1"><span>Conta Corrente</span><div><b></b></div></a><div class="chosen-drop"><div class="chosen-search"><input type="text" autocomplete="off"></div><ul class="chosen-results"><li class="active-result result-selected" style="" data-option-array-index="0">Selecione...</li><li class="active-result result-selected" style="" data-option-array-index="1">Conta Corrente</li><li class="active-result" style="" data-option-array-index="2">Conta Poupança</li></ul></div></div>
        
	</td>
</tr>

<tr class="finalidade_credito_outros_bancos">
	<td class="titulo">Agência (Sem Dígito Verificador)*</td>
	<td>
    	<input id="finalidadeCreditoOutrosBancos.contaBancaria.agencia" name="finalidadeCreditoOutrosBancos.contaBancaria.agencia" onkeypress="Mascara(this,Integer);" onkeyup="Mascara(this,Integer);limparMensagemErro('error.finalidade.agencia')" onkeydown="Mascara(this,Integer);" type="text" value="" size="4" maxlength="4">
        
    </td>
</tr>

<tr class="finalidade_credito_outros_bancos">
	<td class="titulo">Número da Conta*</td>
	<td>
    	<input id="finalidadeCreditoOutrosBancos.contaBancaria.conta" name="finalidadeCreditoOutrosBancos.contaBancaria.conta" onkeypress="Mascara(this,Integer);" onkeyup="Mascara(this,Integer);limparMensagemErro('error.finalidade.conta')" onkeydown="Mascara(this,Integer);" type="text" value="" size="11" maxlength="11">
        
                 
        -
                 
        <input id="digitoVerificadorBB" name="finalidadeCreditoOutrosBancos.contaBancaria.digitoVerificador" onkeyup="limparMensagemErro('error.finalidade.digitoVerificador')" type="text" value="" size="1" maxlength="1">
        <label style="color:#555555; font-size:10px;">(Quando o dígito verificador for a letra 'X',informe 'X')</label>
        
    </td>
</tr>

<tr class="finalidade_credito_outros_bancos">
	<td class="titulo">Banco*</td>
    <td>
    	<select id="cmb_banco" name="finalidadeCreditoOutrosBancos.banco" style="min-width: 150px; display: none;">
			<option value="">Selecione...</option>
			<option value="1800">482 - ARTTA SOCIEDADE DE CRÉDITO DIRETO S.A</option><option value="400">461 - ASAAS IP S.A</option><option value="1">246 - Banco ABC Brasil S.A.</option><option value="2">025 - Banco Alfa S.A.</option><option value="3">641 - Banco Alvorada S.A.</option><option value="4">029 - Banco Banerj S.A.</option><option value="5">000 - Banco Bankpar S.A.</option><option value="6">740 - Banco Barclays S.A.</option><option value="7">107 - Banco BBM S.A.</option><option value="8">031 - Banco Beg S.A.</option><option value="9">739 - Banco BGN S.A.</option><option value="10">096 - Banco BM&amp;FBOVESPA de Serviços de Liquidação e Custódia S.A.</option><option value="11">318 - Banco BMG S.A.</option><option value="12">752 - Banco BNP Paribas Brasil S.A.</option><option value="13">248 - Banco Boavista Interatlântico S.A.</option><option value="14">218 - Banco Bonsucesso S.A.</option><option value="15">065 - Banco Bracce S.A.</option><option value="16">036 - Banco Bradesco BBI S.A.</option><option value="17">204 - Banco Bradesco Cartões S.A.</option><option value="18">394 - Banco Bradesco Financiamentos S.A.</option><option value="19">237 - Banco Bradesco S.A.</option><option value="20">225 - Banco Brascan S.A.</option><option value="21">208 - Banco BTG Pactual S.A.</option><option value="22">044 - Banco BVA S.A.</option><option value="149">336 - Banco C6 S.A.</option><option value="23">263 - Banco Cacique S.A.</option><option value="24">473 - Banco Caixa Geral - Brasil S.A.</option><option value="25">040 - Banco Cargill S.A.</option><option value="26">233 - Banco Cifra S.A.</option><option value="27">745 - Banco Citibank S.A.</option><option value="28">215 - Banco Comercial e de Investimento Sudameris S.A.</option><option value="29">095 - Banco Confidence de Câmbio S.A.</option><option value="30">756 - BANCO COOPERATIVO SICOOB S.A.</option><option value="31">748 - Banco Cooperativo Sicredi S.A.</option><option value="32">222 - Banco Credit Agricole Brasil S.A.</option><option value="33">505 - Banco Credit Suisse (Brasil) S.A.</option><option value="34">229 - Banco Cruzeiro do Sul S.A.</option><option value="35">003 - Banco da Amazônia S.A.</option><option value="36">707 - Banco Daycoval S.A.</option><option value="37">024 - Banco de Pernambuco S.A. - BANDEPE.</option><option value="38">456 - Banco de Tokyo-Mitsubishi UFJ Brasil S.A.</option><option value="39">214 - Banco Dibens S.A.</option><option value="700">335 - Banco Digio S.A.</option><option value="40">001 - Banco do Brasil S.A.</option><option value="41">047 - Banco do Estado de Sergipe S.A.</option><option value="42">037 - Banco do Estado do Pará S.A.</option><option value="43">041 - Banco do Estado do Rio Grande do Sul S.A.</option><option value="44">004 - Banco do Nordeste do Brasil S.A.</option><option value="45">265 - Banco Fator S.A.</option><option value="46">224 - Banco Fibra S.A.</option><option value="47">626 - Banco Ficsa S.A.</option><option value="122">094 - BANCO FINAXIS</option><option value="49">612 - Banco Guanabara S.A.</option><option value="1300">269 - Banco HSBC SA</option><option value="50">063 - Banco Ibi S.A. Banco Múltiplo.</option><option value="51">604 - Banco Industrial do Brasil S.A.</option><option value="52">320 - Banco Industrial e Comercial S.A.</option><option value="53">653 - Banco Indusval S.A.</option><option value="110">077 - BANCO INTER</option><option value="54">249 - Banco Investcred Unibanco S.A.</option><option value="56">479 - Banco ItaúBank S.A.</option><option value="55">184 - Banco Itaú BBA S.A.</option><option value="59">217 - Banco John Deere S.A.</option><option value="57">376 - Banco J. P. Morgan S.A.</option><option value="58">074 - Banco J. Safra S.A.</option><option value="60">600 - Banco Luso Brasileiro S.A.</option><option value="61">389 - Banco Mercantil do Brasil S.A.</option><option value="62">746 - Banco Modal S.A.</option><option value="108">735 - BANCO NEON S.A.</option><option value="63">045 - Banco Opportunity S.A.</option><option value="145">212 - BANCO ORIGINAL</option><option value="64">079 - Banco Original do Agronegócio S.A.</option><option value="65">623 - Banco Panamericano S.A.</option><option value="66">611 - Banco Paulista S.A.</option><option value="600">174 - Banco Pefisa S.A.</option><option value="67">643 - Banco Pine S.A.</option><option value="68">638 - Banco Prosper S.A.</option><option value="69">747 - Banco Rabobank International Brasil S.A.</option><option value="70">356 - Banco Real S.A.</option><option value="71">633 - Banco Rendimento S.A.</option><option value="72">072 - Banco Rural Mais S.A.</option><option value="73">453 - Banco Rural S.A.</option><option value="74">422 - Banco Safra S.A.</option><option value="75">033 - Banco Santander (Brasil) S.A.</option><option value="112">743 - BANCO SEMEAR</option><option value="76">749 - Banco Simples S.A.</option><option value="77">366 - Banco Société Générale Brasil S.A.</option><option value="78">637 - Banco Sofisa S.A.</option><option value="79">012 - Banco Standard de Investimentos S.A.</option><option value="80">464 - Banco Sumitomo Mitsui Brasileiro S.A.</option><option value="150">387 - Banco Toyota do Brasil S.A.</option><option value="81">634 - Banco Triângulo S.A.</option><option value="82">655 - Banco Votorantim S.A.</option><option value="83">610 - Banco VR S.A.</option><option value="84">119 - Banco Western Union do Brasil S.A.</option><option value="85">370 - Banco WestLB do Brasil S.A.</option><option value="601">102 - BANCO XP INVESTIMENTOS</option><option value="300">348 - Banco XP S.A.</option><option value="86">021 - BANESTES S.A. Banco do Estado do Espírito Santo.</option><option value="87">719 - Banif-Banco Internacional do Funchal (Brasil)S.A.</option><option value="88">755 - Bank of America Merrill Lynch Banco Múltiplo S.A.</option><option value="89">073 - BB Banco Popular do Brasil S.A.</option><option value="120">121 - BCO AGIPLAN S.A.</option><option value="144">654 - BCO A.J. RENNER S.A.</option><option value="136">213 - BCO ARBI S.A.</option><option value="131">122 - BCO BRADESCO BERJ S.A.</option><option value="124">412 - BCO CAPITAL S.A.</option><option value="130">266 - BCO CEDULA S.A.</option><option value="128">241 - BCO CLASSICO S.A.</option><option value="121">083 - BCO DA CHINA BRASIL S.A.</option><option value="113">757 - BCO KEB HANA DO BRASIL S.A.</option><option value="129">300 - BCO LA NACION ARGENTINA</option><option value="133">243 - BCO MÁXIMA S.A.</option><option value="138">613 - BCO PECUNIA S.A.</option><option value="135">494 - BCO REP ORIENTAL URUGUAY BCE</option><option value="111">741 - BCO RIBEIRAO PRETO S.A.</option><option value="132">120 - BCO RODOBENS S.A.</option><option value="137">018 - BCO TRICURY S.A.</option><option value="125">124 - BCO WOORI BANK DO BRASIL S.A.</option><option value="90">250 - BCV - Banco de Crédito e Varejo S.A.</option><option value="91">078 - BES Investimento do Brasil S.A.-Banco de Investimento.</option><option value="200">274 - BMP SCMEPP LTDA</option><option value="134">017 - BNY MELLON BCO S.A.</option><option value="92">069 - BPN Brasil Banco Múltiplo S.A.</option><option value="93">125 - Brasil Plural S.A. - Banco Múltiplo.</option><option value="94">070 - BRB - Banco de Brasília S.A.</option><option value="95">104 - Caixa Econômica Federal.</option><option value="117">085 - CCC CECRED</option><option value="140">090 - CCCM SICOOB UNIMAIS</option><option value="116">097 - CCC NOROESTE BRASILEIRO LTDA.</option><option value="139">089 - CCR REG MOGIANA</option><option value="118">114 - CENTRAL CECM ESP. SANTO</option><option value="96">477 - Citibank S.A.</option><option value="1400">542 - CLOUDWALK INSTITUIÇÃO DE PAGAMENTO E SERVICOS LTDA</option><option value="127">163 - COMMERZBANK BRASIL S.A. - BCO MÚLTIPLO</option><option value="119">133 - CONFEDERACAO NAC DAS CCC SOL</option><option value="109">136 - CONF NAC COOP CENTRAIS UNICRED</option><option value="153">403 - CORA SOCIEDADE DE CRÉDITO DIRETO S.A.</option><option value="142">098 - CREDIALIANÇA CCR</option><option value="143">010 - CREDICOAMO</option><option value="97">487 - Deutsche Bank S.A. - Banco Alemão.</option><option value="800">301 - DOCK INSTITUIÇÃO DE PAGAMENTO S.A.</option><option value="500">364 - EFÍ S.A. - INSTITUIÇÃO DE PAGAMENTO</option><option value="1600">382 - FIDUCIA SCMEPP LTDA</option><option value="1900">450 - FITS INSTITUIÇÃO DE PAGAMENTO S.A.</option><option value="98">064 - Goldman Sachs do Brasil Banco Múltiplo S.A.</option><option value="99">062 - Hipercard Banco Múltiplo S.A.</option><option value="100">399 - HSBC Bank Brasil S.A. - Banco Múltiplo.</option><option value="126">132 - ICBC DO BRASIL BM S.A.</option><option value="101">492 - ING Bank N.V.</option><option value="1500">670 - IP4Y INSTITUICAO DE PAGAMENTO LTDA</option><option value="102">652 - Itaú Unibanco Holding S.A.</option><option value="103">341 - Itaú Unibanco S.A.</option><option value="104">488 - JPMorgan Chase Bank.</option><option value="1700">559 - KANASTRA CFI</option><option value="154">323 - MERCADO PAGO IP LTDA.</option><option value="900">536 - NEON PAGAMENTOS S.A.</option><option value="141">753 - NOVO BCO CONTINENTAL S.A. - BM</option><option value="146">260 - Nu Pagamentos S.A</option><option value="1200">712 - OURIBANK S.A. BANCO MÚLTIPLO</option><option value="148">290 - PAGSEGURO</option><option value="123">254 - PARANA BCO S.A.</option><option value="151">380 - PICPAY SERVICOS S.A.</option><option value="1100">529 - Pinbank Brasil Instituição de Pagamento S.A.</option><option value="152">329 - QI Sociedade de Crédito Direto S.A.</option><option value="105">751 - Scotiabank Brasil S.A. Banco Múltiplo.</option><option value="1000">363 - SINGULARE CTVM S.A</option><option value="147">197 - STONE PAGAMENTOS S.A.</option><option value="106">409 - UNIBANCO - União de Bancos Brasileiros S.A.</option><option value="107">230 - Unicard Banco Múltiplo S.A.</option><option value="115">099 - UNIPRIME CENTRAL CCC LTDA.</option><option value="114">084 - UNIPRIME NORTE DO PARANÁ - CC</option>								
	    </select><div class="chosen-container chosen-container-single" style="width: 394px;" title="" id="cmb_banco_chosen"><a class="chosen-single" tabindex="-1"><span>260 - Nu Pagamentos S.A</span><div><b></b></div></a><div class="chosen-drop"><div class="chosen-search"><input type="text" autocomplete="off"></div><ul class="chosen-results"><li class="active-result result-selected" style="" data-option-array-index="159"><em>260</em> - Nu Pagamentos S.A</li></ul></div></div>
        
	</td>
</tr>
<tr class="finalidade_credito_outros_bancos" id="cpf_cnpj_titular_finalidade_credito_outros_bancos" style="">
    <td class="titulo">CPF/CNPJ do Titular*
        









<span title="O titular somente poderá ser o Beneficiário,Procurador ou Representante Legal desta Solicitação. Preencha o CPF ou CNPJ sem formatação." class="bt-acao-ajuda"> </span>
    </td>
    <td>
        

































        
        
<div style="float:left">
	<input id="finalidadeCreditoOutrosBancos_titular_cpfCnpj" name="finalidadeCreditoOutrosBancos.titular.cpfCnpj" onkeydown="Mascara(this,CpfCnpjContagem);" onblur="validaCpfCnpj_finalidadeCreditoOutrosBancos_titular_cpfCnpj();" onchange="Mascara(this,CpfCnpjContagem);" type="text" value="" size="40" maxlength="18">
	





















<input type="button" id="finalidadeCreditoOutrosBancos_titular_cpfCnpj_button" class="botaoAtualizar invisivel" value="Validar" onclick="executarAcao_finalidadeCreditoOutrosBancos_titular_cpfCnpj_button()">

<script type="text/javascript">

	function executarAcao_finalidadeCreditoOutrosBancos_titular_cpfCnpj_button(){
				
                
	            var retorno = true;

                
                        retorno = validaCpfCnpj_finalidadeCreditoOutrosBancos_titular_cpfCnpj();
                
        
                
                        
                if(retorno) {
                        
                }
	}
</script>

	<span id="span_finalidadeCreditoOutrosBancos_titular_cpfCnpj" class="invisible"></span>
	
        <br>
        <label id="lb_msg_cpf_cnpj_quantidade_digitos" style="color:#555555; font-size:10px;">(Informe 11 (onze) digitos para CPF ou 14 (quatorze) para CNPJ)</label>
</div>
<script type="text/javascript">
function validaCpfCnpj_finalidadeCreditoOutrosBancos_titular_cpfCnpj() {
        $("#finalidadeCreditoOutrosBancos_titular_nome").val("");
	var cpfCnpj = Integer($("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").val());
	cpfCnpj = cpfCnpj.replace(/[-./]/g, '');
	if(cpfCnpj == "") {
		
		    $("#finalidadeCreditoOutrosBancos_titular_nome").val("");
		    
		    
		    
		    $("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").addClass('invisible');
		    $("#tribunais_ajaxGif_finalidadeCreditoOutrosBancos_titular_cpfCnpj_button").hide();
		    $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj_button").removeAttr("disabled");
		
		return true;
	}

	if("CPFCNPJ" === 'CPFCNPJ'){

		if($("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").val().length!=14 && $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").val().length!=18){
		            aplicaResultado_finalidadeCreditoOutrosBancos_titular_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	if("CPFCNPJ" === 'CPF'){

		if($("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").val().length!=14){
		            aplicaResultado_finalidadeCreditoOutrosBancos_titular_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	if("CPFCNPJ" === 'CNPJ'){

		if($("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").val().length!=18){
		            aplicaResultado_finalidadeCreditoOutrosBancos_titular_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	
	$("#tribunais_ajaxGif_finalidadeCreditoOutrosBancos_titular_cpfCnpj_button").show();
		
	// realiza chamada WS
	$("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").trigger("eventIniciarRequisicaoAjax");
        
        
        //validar cpfcnpj nas partes do processo e no bb ou somento no bb
        if(false){
                var opt = $("#cb_tipoBeneficiario > option:checked");
                var tipo = opt.attr('tipo');
                var url = "/portaltrtsp/pages/processo/tribunal/"+$("#numeroProcesso").val()+"/cpfcnpj/"+cpfCnpj+"/"+tipo+"/validar.json";
        }else{      
                var url = "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validarModulo.json";
                
                        url = "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validar.json";
                
        }
        
        var ajaxReq = $.ajax(url, {
                dataType: "text",

                statusCode: {
                        200: function() { 
                                $("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").removeClass('fieldWithErrors');
                                aplicaResultado_finalidadeCreditoOutrosBancos_titular_cpfCnpj("");
                                   
                        },
                        204: function() { 
                                aplicaResultado_finalidadeCreditoOutrosBancos_titular_cpfCnpj("O CPF/CNPJ inválido ou formato incorreto."); 
                                $("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").addClass('fieldWithErrors');
                        },
                        404: function() { 
                                aplicaResultado_finalidadeCreditoOutrosBancos_titular_cpfCnpj("Serviço WS para acessos externos não encontrado."); 
                                $("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").addClass('fieldWithErrors');
                        },
                        406: function() { 
                                aplicaResultado_finalidadeCreditoOutrosBancos_titular_cpfCnpj("A consulta processual não retornou dados do CPF/CNPJ da parte informada."); 
                                $("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").addClass('fieldWithErrors');
                        },
                        500: function() { 
                                aplicaResultado_finalidadeCreditoOutrosBancos_titular_cpfCnpj("Serviço externo indisponível. Tente novamente mais tarde."); 
                                $("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").addClass('fieldWithErrors');
                        },
                        503: function() { 
                                aplicaResultado_finalidadeCreditoOutrosBancos_titular_cpfCnpj("Serviço externo indisponível. Tente novamente mais tarde."); 
                                $("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").addClass('fieldWithErrors');
                        },
                        666: function(xhr) { 
                               console.log(xhr.responseText);
                              $("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").removeClass('fieldSuccess');
                              $("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").removeClass('fieldWithErrors');
                              $("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").removeClass('invisible');	
                              $("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").addClass('fieldWithErrors');
                              aplicaResultado_finalidadeCreditoOutrosBancos_titular_cpfCnpj(xhr.responseText);                        
                        }
                },

                
                        success: function(data, textStatus, jqXHR) {
                                $("#finalidadeCreditoOutrosBancos_titular_nome").val(data);
                                
                },
                

                complete: function() {
                    $("#tribunais_ajaxGif_finalidadeCreditoOutrosBancos_titular_cpfCnpj_button").hide();
                    $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj_button").removeAttr("disabled");

                    
                        $("#finalidadeCreditoOutrosBancos_titular_nome\\.errors").hide();
                    

                    $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").trigger("eventFinalizarRequisicaoAjax");
                }
        });
	
	return true;
}

function aplicaResultado_finalidadeCreditoOutrosBancos_titular_cpfCnpj(validacaoMsg) {
	if(validacaoMsg != ""){
		$("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").removeClass('invisible');	
	}else{
		$("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").addClass('invisible');
	}
    $("#span_finalidadeCreditoOutrosBancos_titular_cpfCnpj").html(validacaoMsg);
    
    
	    if(validacaoMsg == "") {
			$("#finalidadeCreditoOutrosBancos_titular_nome").attr("readonly", "readonly");
	    } else {
	    			
	    }
    
    
//    if(document.getElementById('cb_tipoFinalidade') != null){
//        var tp_finalidade = document.getElementById('cb_tipoFinalidade').value;
//        console.log("finalidade <:> " + tp_finalidade );
//        if(tp_finalidade === "PIX"){
//           //  this.montaComboTitularConta();
//            // window.addEventListener("load", function(){
//                    montaComboTitularConta(); 
//            //    });
//         }
//     }  
}



</script>
    </td>
</tr>
<tr class="finalidade_credito_outros_bancos" id="nome_titular_finalidade_credito_outros_bancos" style="">
    <td class="titulo">Nome do Titular*</td>
    <td>
        <input id="finalidadeCreditoOutrosBancos_titular_nome" name="finalidadeCreditoOutrosBancos.titular.nome" type="text" value="" size="45" maxlength="100" readonly="readonly">
        
    </td>
</tr>
<tr class="finalidade_credito_outros_bancos" id="linhaChavePixCpfCnpjBeneficiario" style="opacity: 1; display: none;">
    <td class="titulo">CPF/CNPJ do Titular* 
       









<span title="O titular somente poderá ser o Beneficiário,Procurador ou Representante Legal desta Solicitação. Preencha o CPF ou CNPJ sem formatação." class="bt-acao-ajuda"> </span>
    </td>
    <td id="text_cpfcnpjtitularconta">
        <select id="select_titular" onchange="preecherCamposTransicaoCpfCnpjNomeFinalidadePIX()" class="pixEstilo">  
        <option value="">SELECIONE...</option><option value="219.974.718-25 - SELMA MARIA DOMINGOS ">219.974.718-25 -SELMA MARIA DOMINGOS </option><option value="40.160.266/0001-16 - VICTOR GOBBO SOCIEDADE INDIVIDUAL DE ADVOCACIA">40.160.266/0001-16 -VICTOR GOBBO SOCIEDADE INDIVIDUAL DE ADVOCACIA</option></select>
    </td>    
</tr>















<script type="text/javascript">
        
        $(document).ready(function(){
            initReload();
        });
        
        function configurarCamposTipoResgate() {
            
            var tipoResgate = $("#cb_tipoResgate").val();
            
            if (tipoResgate !== null && tipoResgate !== "") {

                exibirLinhasTipoResgate();
            } else {
                esconderLinhasTipoResgate();
            }
        }
        
        function selecionarTipoResgate() {
            
            var tipoResgate = $("#cb_tipoResgate").val();
            
            if (tipoResgate === "RESGATE_VALOR_REAL_INFORMADO") {
                $("#valor_real").val("");
                $("#rb_comCorrecao").prop("checked", false);
                $("#rb_semCorrecao").prop("checked", false);
                $("#rb_semCorrecao").prop("disabled", false);
                //$("#valor_real").removeAttr("readonly");
                
                if (!($("#cb_tipoFinalidade").val() === "GRU" || $("#cb_tipoFinalidade").val() === "GPS" || $("#cb_tipoFinalidade").val() === "DARF")) {
                    $("#valor_real").removeAttr('readOnly');
                }
            }

            if (tipoResgate === "RESGATE_VALOR_TOTAL") {
                $("#rb_comCorrecao").prop("checked", true);
                $("#rb_semCorrecao").prop("checked", false);
                $("#rb_semCorrecao").prop("disabled", true);
                $("#valor_real").attr("readonly", true);
                selecionarContaComParcelaSelecionada();
            }
            
            configurarCamposTipoResgate();
        }
        
        function exibirLinhasTipoResgate() {
            $("#linhaValorSolicitacao").fadeIn();
            $("#linhaValorLevantamento").fadeIn();
        }
        
        function esconderLinhasTipoResgate() {
            $("#linhaValorSolicitacao").fadeOut();
            $("#linhaValorLevantamento").fadeOut();
        }
        
        function criarMascara(){
               $(".mascara_valor").maskMoney({
                        thousands: '.',
                        decimal: ','
                }); 
        }
    
        function initReload(){
            criarMascara();
            configurarCamposTipoResgate();
        }
        
</script>
<tr id="linhaTipoResgate" class="finalidade_comparecer_ao_banco">
        <td class="titulo">
                Tipo de Resgate*
        </td>
        <td>
                <select id="cb_tipoResgate" name="solicitacaoTransiente.tipoQualificador" onchange="selecionarTipoResgate();" style="display: none;">
                         <option value="">Selecione...</option>
                         <option value="RESGATE_VALOR_REAL_INFORMADO">Valor Real Informado</option><option value="RESGATE_VALOR_TOTAL">Valor Total da Conta </option>
                </select><div class="chosen-container chosen-container-single" style="width: 235px;" title="" id="cb_tipoResgate_chosen"><a class="chosen-single" tabindex="-1"><span>Valor Real Informado</span><div><b></b></div></a><div class="chosen-drop"><div class="chosen-search"><input type="text" autocomplete="off"></div><ul class="chosen-results"><li class="active-result result-selected" style="" data-option-array-index="0">Selecione...</li><li class="active-result result-selected" style="" data-option-array-index="1">Valor Real Informado</li><li class="active-result" style="" data-option-array-index="2">Valor Total da Conta </li></ul></div></div>
                
        </td>
        
</tr>
<tr id="linhaValorSolicitacao" class="finalidade_comparecer_ao_banco" style="opacity: 1; display: table-row;">
        <td class="titulo">
                Valor (R$)*
        </td>
        <td>
                <input id="valor_real" name="solicitacaoTransiente.valorReal" class="mascara_valor" type="text" value="0,00" size="40" maxlength="20"> 
                (Do valor informado poderão ser descontados impostos e taxas.)
                
                
        </td>
</tr>
<tr id="linhaValorLevantamento" class="finalidade_comparecer_ao_banco" style="opacity: 1; display: table-row;">
        <td class="titulo">
                Valor do Levantamento*
        </td>
        <td>
                <input id="rb_comCorrecao" name="solicitacaoTransiente.baseCalculo" type="radio" value="COM_ACRESCIMO"> 
                Com Correção 
                <input id="rb_semCorrecao" name="solicitacaoTransiente.baseCalculo" type="radio" value="SEM_ACRESCIMO"> 
                Sem Correção
                
        </td>
        
</tr>

<style type="text/css">

.pixEstilo {
    position: relative !important;
    display: block;
    overflow: hidden;
    padding: 0 0 0 8px !important;
    height: 23px;
    border: 1px solid #aaa !important;
    border-radius: 5px;
    background-clip: padding-box;
    box-shadow: 0 0 3px #e3dede inset, 0 1px 1px rgba(0, 0, 0, 0.1);
    color: #444;
    text-decoration: none;
    white-space: nowrap;
    line-height: 24px;
    width: 234px;
    background-color: ghostwhite;
    cursor: pointer;
    font-size: smaller !important;
}
        
</style>

<script type="text/javascript">
        
        //Permitir apenas inserï¿½ï¿½o da letra x para caracteres alfabï¿½ticos
        $("#digitoVerificadorBB").on({change:function(){
                        verificarDigito();         
                },keypress:function(event){
                        verificarTecla(event);
                },keydown:function(event){
                        verificarTecla(event);         
                },keyup:function(event){
                        verificarTecla(event);         
                }});
        
        function verificarTecla(event){
                var key = (event.which) ? event.which : event.keyCode;
                if(key>=65 && key<=90 && key!==88){
                        if($("#digitoVerificadorBB").val().length>0){
                                $("#digitoVerificadorBB").val('');   
                        }
                }
        }
        function verificarDigito(){
                var digito =  $("#digitoVerificadorBB").val();
                if(digito!=='x' && digito!=='X' && !$.isNumeric(digito)){
                        $("#digitoVerificadorBB").val('');   
                }else if(digito==='x'){
                        $("#digitoVerificadorBB").val('X');   
                }
        }
</script>
                                        
                                        
                                        
                                        
                                        
                                        
                                         
                                        
                                
                        
                
                        
                
                                
                        </tbody>
                        
                                <tfoot>
                                        <tr>
                                                <td class="act_td" colspan="2">
                                                        <span class="bt_acessibilidade" title="Adicionar">
                                                                
                                                                        





















<input type="button" id="bt_add_solicitacao" class="botaoNovo" value="" onclick="executarAcao_bt_add_solicitacao()">

<script type="text/javascript">

	function executarAcao_bt_add_solicitacao(){
				
                
	            var retorno = true;

                
                        retorno = validarRequisicoesPendentes();
                
        
                
                        
                if(retorno) {
                        
                                
                                        $("#form_alvara").attr("action","/portaltrtsp/pages/mandado/pagamento/gerarSolicitacao");
                                        $("#form_alvara").submit();
                                 
                        
                }
	}
</script>

                                                                
                                                        </span>
                                                </td>
                                        </tr>
                                </tfoot>
                        
                </table>




INSS

Número de referência = CPF do autor
Data da apuração = data do depósito selecionado
Data do vencimento = último dia do mês corrente

<form id="form_alvara" action="/portaltrtsp/pages/mandado/pagamento/carregarfinalidade/ajax.do" method="post">
        <h2>
                Alvará 
                
                    
                        Gravado
                        
                
                
                     
                        20261005222500078477
                        
                
        <botao id="avjt-certificar-siscondj-protocolo" class="informacoes avjt-siscondj avjt-azul" aria-label="Abre a Tarefa &quot;Anexar Documento&quot; e minuta o texto">CERTIFICAR PROTOCOLO</botao><botao id="avjt-certificar-siscondj-conferencia" class="informacoes avjt-siscondj avjt-preto" aria-label="Abre a Tarefa &quot;Anexar Documento&quot; e minuta o texto">CERTIFICAR CONFERÊNCIA</botao></h2>
        
        


















        
        
                
                        <div id="divImpressao">
                        <table id="table_processo" class="relatorio">
                                <caption>Processo</caption>
                                <tbody><tr>
                                        <td class="right">Número do Processo:</td>
                                        <td class="left">1000975-77.2025.5.02.0703<a id="maisPJe_atalhoConsultaPJe" style="display: inline-block; position: absolute; z-index: 100; width: 28px; height: 28px; text-align: center; color: black;" title="Consultar Processo no PJe (Atalho: F2)"><i class="search" style="display: inline-block; font-style: normal; font-variant: normal; text-rendering: auto; line-height: 1; cursor: pointer; width: 2vh; height: 2vh; background-color: black;"></i></a></td>
                                </tr>
                                <tr>
                                        <td class="right">Jurisdição:</td>
                                        <td class="left">São Paulo - Zona Sul</td>
                                </tr>
                                
                                
                                        
                                <tr>
                                        <td class="right">
                                                
                                                        
                                                        
                                                        
                                                                Órgão/Vara:
                                                        
                                                
                                        </td>
                                        <td class="left">3ª VARA DO TRABALHO DE SÃO PAULO - ZONA SUL</td>
                                </tr>
                                
                                <tr>
                                        <td class="right">Partes:</td>
                                        <td>
                                                <table id="table_partes" style="text-align: left;">
                                                        <tbody><tr>
                                                                <th>Tipo</th>
                                                                <th>Nome</th>
                                                                <th>CPF/CNPJ</th>
                                                        </tr>
                                                        <tr>
                                                                <td style="text-align: left;">Autor</td>
                                                                <td style="text-align: left;">SELMA MARIA DOMINGOS</td>
                                                                <td style="text-align: left;">219.974.718-25</td>
                                                        </tr>
                                                        <tr>
                                                                <td style="text-align: left;">Adv. Autor</td>
                                                                <td style="text-align: left;">VICTOR GOBBO LAMEIRINHAS</td>
                                                                <td style="text-align: left;">318.448.818-73</td>
                                                        </tr>

                                                        <tr>
                                                                <td style="text-align: left;">Réu</td>
                                                                <td style="text-align: left;">HOSPITAL E MATERNIDADE VIDA'S LTDA.</td>
                                                                <td style="text-align: left;">96.534.300/0001-20</td>
                                                        </tr>

                                                        <tr>
                                                                <td style="text-align: left;">Adv. Réu</td>
                                                                <td style="text-align: left;">MONICA LOURENCO DE CAMPOS SILVA</td>
                                                                <td style="text-align: left;">379.477.938-08</td>
                                                        </tr>

                                                </tbody></table>
                                        </td>
                                </tr>

                        </tbody></table>
                        </div>
                
        
           
        
        <input id="alvara.id" name="alvara.id" type="hidden" value="2566475">
        <input id="solicitacaoTransiente.id" name="solicitacaoTransiente.id" type="hidden" value="">
        <input id="idProcesso" name="processo.id" type="hidden" value="11073364">
        <input id="paginaAnterior" name="paginaAnterior" type="hidden" value="MOVIMENTACAO">
        <input id="numeroProcesso" name="processo.numero" type="hidden" value="10009757720255020703">
        <input id="numeroProcessoPrecatorio" name="numeroProcessoPrecatorio" type="hidden" value="">
        <input id="numeroPrecatorio" name="numeroPrecatorio" type="hidden" value="">
        <input type="hidden" name="alvaraPrecatorio" value="false">
        
           
        
        
        
        
                <br>
                <br>
                <br>
                















<table id="tbSolicitacoes" class="formulario">
        <caption>
                Adicionar Solicitações Judiciais
                <br>
                <label style="font-size:0.8em; font-weight: normal;">(Selecione uma conta)</label>
        </caption>
	<tbody>
		<tr>
			<td></td>
			<td>
				<div class="a-menu" style="margin: 2px; width: 180px; cursor: pointer;" onclick="omitirContasZeradas();">
					<div class="bt-acao-visualizar" id="imgOmitirContasZeradas" style="margin-right: 8px;"></div>
					<div id="labelOmitirContasZeradas" style="padding-top: 6px;">Omitir contas zeradas</div>
				</div>				
			</td>
		</tr>
	    <tr>
            <td class="titulo">
				Contas Judiciais do Processo*
			</td>
			<td>

				<table id="contas_processo" class="relatorio">
					<thead>
						<tr>
							<th width="2%"></th>
                                                        <th width="2%"></th>
							<th width="12%">Número da Conta Judicial</th>
							<th width="12%">Valor Depositado</th>
                                                        <th width="12%">Valor Agendado</th>
                                                        <th width="12%">Valor Bloqueado</th>
                                                        <th width="12%">Valor Disponível</th>
						</tr>
						
					</thead>
					<tbody>
                                                
                                                        
                                                                
                                                                        <tr id="linhaConta_2976855" style="background-color: #EEE; cursor:pointer;">
                                                                                <td align="center">
                                                                                        
                                                                                            <img id="ico-img" style="width: 18px;" src="/portaltrtsp/images/subtracao-ico.png" onclick="abrirParcelasEvent(2976855,event)" alt="Parcelas">
                                                                                        
                                                                                </td>
                                                                                
                                                                                        
                                                                                        
                                                                                                <td align="center" onclick="abrirParcelasEvent(2976855,event);">
                                                                                                        
                                                                                                                <input id="contasSelecionadas_2976855" name="contasSelecionadas" saldo="-1" onchange="selecionarConta(2976855);" type="checkbox" value="2976855" style="display: inline-block;"><input type="hidden" name="_contasSelecionadas" value="on">
                                                                                                        
                                                                                                </td>
                                                                                        
                                                                                
                                                                                
                                                                                        
                                                                                        
                                                                                                <td align="center" onclick="abrirParcelasEvent(2976855,event);">
                                                                                                        600128877743
                                                                                                </td>
                                                                                        
                                                                                
                                                                                
                                                                                        
                                                                                                <td id="td_saldo_conta_2976855" align="center">R$ 44.062,07</td>
                                                                                                <td id="td_valor_agendado_2976855" align="center">R$ 9.164,04</td>
                                                                                                <td id="td_valor_bloqueado_2976855" align="center">R$ 0,00</td>
                                                                                                <td id="td_saldo_corrigido_conta_2976855" align="center">R$ 14.530,90</td>
                                                                                        
                                                                                        
                                                                                

                                                                        </tr>
                                                                        
                                                                                <tr class="subtabela" id="contaId_2976855" style="display: table-row;">
                                                                                        
                                                                                                <td colspan="8">
																										<table style="width: 100%; margin-top: 4px;">
																											<tbody>
																												<tr>
																													<td style="width: 62px; text-align: right;">
						                                                                                                <input type="checkbox" id="checkBoxOmitirParcelasZeradas_2976855" name="checkBoxOmitirParcelasZeradas" onchange="omitirParcelasZeradas(2976855)">
																													</td>
																													<td style="width: 200px; text-align: left;">
			                                                                                       						<label for="checkBoxOmitirParcelasZeradas_2976855" style="cursor: pointer;">Omitir parcelas zeradas</label>
																													</td>
																													<td style="width: auto;">
																													</td>
																												</tr>
																											</tbody>
																										</table>
                                                                                                        <table class="subrelatorio" id="tabela_parcelas_conta_2976855">
                                                                                                                <tbody><tr>
																													<!-- <th colspan="2">&nbsp;</th>-->
                                                                                                                    <th>&nbsp;</th>
                                                                                                                    <th style="background-color: #F0F0F0;width:80px;">Nº Parcela</th>
                                                                                                                    <th style="background-color: #F0F0F0;width:140px;">Data do Deposito</th>
                                                                                                                    <th style="background-color: #F0F0F0;width:260px;">Nome do Depositante</th>
                                                                                                                    <th style="background-color: #F0F0F0;width:160px;">CPF/CNPJ Depositante</th>
                                                                                                                    <th style="background-color: #F0F0F0;width:150px;">Valor Depositado</th>
                                                                                                                    <th style="background-color: #F0F0F0;width:150px;">Valor Agendado</th>
                                                                                                                    <th style="background-color: #F0F0F0;width:150px;">Valor Bloqueado</th>
                                                                                                                    <th style="background-color: #F0F0F0;width:150px;">Valor Disponível</th>
                                                                                                                    <!--<th colspan="2">&nbsp;</th>-->
                                                                                                                </tr>
                                                                                                                

                                                                                                                    <tr id="linhaParcela_2976855_5412479">
                                                                                                                        <!--<td >&nbsp;</td>-->
                                                                                                                        <td style="text-align: center;">
                                                                                                                                
                                                                                                                                        <input id="parcelasSelecionadas_2976855_5412479" name="parcelasSelecionadas" saldo="-1" onchange="selecionarParcela(2976855, 5412479)" type="checkbox" value="5412479"><input type="hidden" name="_parcelasSelecionadas" value="on">
                                                                                                                                
                                                                                                                        </td>
                                                                                                                        <td style="text-align: center;">1</td>
                                                                                                                        <td style="text-align: center;">25/08/2026</td>
                                                                                                                        <td style="text-align: center;">VIACAO METROPOLE PAULISTA S/A</td>
                                                                                                                        <td style="text-align: center;">31.974.104/0001-20</td>
                                                                                                                        <td id="td_saldo_parcela_depositado_5412479" style="text-align: center; cursor:pointer;">R$ 0,00</td>
                                                                                                                        <td id="td_saldo_parcela_agendado_5412479" style="text-align: center; cursor:pointer;">R$ 0,00</td>
                                                                                                                        <td id="td_saldo_parcela_bloqueado_5412479" align="center" style="text-align: center; cursor:pointer;">R$ 0,00</td>
                                                                                                                        <td id="td_saldo_parcela_saldo_5412479" style="text-align: center; cursor:pointer;">R$ 0,00</td>
                                                                                                                        <!--<td colspan="2">&nbsp;</td>-->
                                                                                                                    </tr>
                                                                                                                

                                                                                                                    <tr id="linhaParcela_2976855_5475545">
                                                                                                                        <!--<td >&nbsp;</td>-->
                                                                                                                        <td style="text-align: center;">
                                                                                                                                
                                                                                                                                        <input id="parcelasSelecionadas_2976855_5475545" name="parcelasSelecionadas" saldo="-1" onchange="selecionarParcela(2976855, 5475545)" type="checkbox" value="5475545"><input type="hidden" name="_parcelasSelecionadas" value="on">
                                                                                                                                
                                                                                                                        </td>
                                                                                                                        <td style="text-align: center;">2</td>
                                                                                                                        <td style="text-align: center;">25/09/2026</td>
                                                                                                                        <td style="text-align: center;">VIACAO METROPOLE PAULISTA S/A</td>
                                                                                                                        <td style="text-align: center;">31.974.104/0001-20</td>
                                                                                                                        <td id="td_saldo_parcela_depositado_5475545" style="text-align: center; cursor:pointer;">R$ 23.665,03</td>
                                                                                                                        <td id="td_saldo_parcela_agendado_5475545" style="text-align: center; cursor:pointer;">R$ 9.164,04</td>
                                                                                                                        <td id="td_saldo_parcela_bloqueado_5475545" align="center" style="text-align: center; cursor:pointer;">R$ 0,00</td>
                                                                                                                        <td id="td_saldo_parcela_saldo_5475545" style="text-align: center; cursor:pointer;">R$ 14.530,90</td>
                                                                                                                        <!--<td colspan="2">&nbsp;</td>-->
                                                                                                                    </tr>
                                                                                                                
                                                                                                        </tbody></table>

                                                                                                </td>
                                                                                        
                                                                                </tr>
                                                                        
                                                                
                                                        
                                                        
                                                
					</tbody>
		     	</table>

			</td>
		</tr>

		<tr id="totalSelecionado" class="cor_azul">
			<td class="titulo cor_azul" style="background-color: #ffffff;  padding: 0;">
                                Saldo Disponível</td>
			<td class="cor_azul">
				<label id="somaValorTotalSelecionado">14.530,90</label>
				<input id="valorTotalSelecionado" name="valorTotalSelecionado" type="hidden" value="14.530,90">
			</td>
		</tr>
	</tbody>
</table>
                <div id="dialog_ajax" class="invisivel" title="Resumo da alteração">
                </div>

<script type="text/javascript">
		var fgOmitirContasZeradas = false;

		$(document).ready(function() {
			atualizarDados();
        });
		
		function atualizarDados(){
			
				atualizarExibicaoContasEParcelas(2976855);
			

			$("#tbSolicitacoes").find("input[id^=contasSelecionadas_]").change(function(){
					atualizarValorTotalSelecionado();
			});

			$("#tbSolicitacoes").find("input[id^=parcelasSelecionadas_]").change(function(){
					atualizarValorTotalSelecionado();
			});

			exibirDadosRecarregados();
			setTimeout(() => {
                
                    carregarContasAjax(2976855);
                
            }, 1000);
		}
	
        function omitirContasZeradas(){
        	fgOmitirContasZeradas = !fgOmitirContasZeradas;
            //
            if (fgOmitirContasZeradas){
            	document.getElementById("imgOmitirContasZeradas").className = "bt-acao-esconder"; 
            	document.getElementById("labelOmitirContasZeradas").textContent = "Exibir contas zeradas"; 
            } else {
            	document.getElementById("imgOmitirContasZeradas").className = "bt-acao-visualizar"; 
            	document.getElementById("labelOmitirContasZeradas").textContent = "Omitir contas zeradas"; 
            }
            var tblContas = document.getElementById("contas_processo");
            for (var i = 1; i<tblContas.rows.length; i++){
            	if (i%2 == 0)
            		continue;
                var idConta = tblContas.rows[i].id.replace("linhaConta_", "");
            	var fgContaZerada = tblContas.rows[i].cells[6].innerText=='R$ 0,00' || 
									tblContas.rows[i].cells[6].innerText=='R$ 0.00' ||
									tblContas.rows[i].cells[6].innerText=='0,00' ||
									tblContas.rows[i].cells[6].innerText=='0.00';
                var attrIcoImg = $("#linhaConta_"+idConta+" img#ico-img").attr("src");
            	if (fgOmitirContasZeradas && fgContaZerada){
                	tblContas.rows[i].style.display = 'none';
                	tblContas.rows[i+1].style.display = 'none';
            	} else {
                	tblContas.rows[i].style.display = '';
                	if (attrIcoImg.includes('subtracao-ico')) tblContas.rows[i+1].style.display = '';
            	}
            }
        }

        function omitirParcelasZeradas(id){
        	var fgOmitirParcelasZeradas = document.getElementById("checkBoxOmitirParcelasZeradas_"+id).checked;
            var tblParcelas = document.getElementById("tabela_parcelas_conta_"+id);
            for (var i = 1; i<tblParcelas.rows.length; i++){
            	var fgParcelaZerada = tblParcelas.rows[i].cells[8].innerText=='R$ 0,00' || 
						              tblParcelas.rows[i].cells[8].innerText=='R$ 0.00' ||
						              tblParcelas.rows[i].cells[8].innerText=='0,00' ||
						              tblParcelas.rows[i].cells[8].innerText=='0.00';
            	if (fgOmitirParcelasZeradas && fgParcelaZerada){
            		tblParcelas.rows[i].style.display = 'none';
            	} else {
            		tblParcelas.rows[i].style.display = '';
            	}
            }
        }

        function exibirDadosRecarregados(){
                $("#selecao_tipoBeneficiario").find("input:checked[type=checkbox][id^=rb_procurador]").each(function(){
                        exibirConteudoProcurador();
                });
                $("#selecao_tipoBeneficiario").find("input:checked[type=checkbox][id^=rb_representanteLegal]").each(function(){
                        exibirConteudoRepresentanteLegal();
                });
                if($("#cb_tipoResgate").val()!==undefined){
                        initReload();
                }
        }

        function atualizarExibicaoContasEParcelas(idConta){
                var selecionada = false;
                //manter contas ou parcelas selecionadas abertas
                //parcela
            //    debugger;
                $("#tabela_parcelas_conta_"+idConta).find("input:checked[type=checkbox][id^=parcelasSelecionadas_]").each(function(){
                        $("#contaId_"+idConta).show();
                        $("#linhaConta_"+idConta+" img#ico-img").attr("src", "/portaltrtsp/images/subtracao-ico.png");
                        $("#contaId_"+idConta).find("input[type=checkbox][id^=parcelasSelecionadas_]").each(function(){
                                selecionada =true;
                                $("#totalSelecionado").removeClass("invisivel");
                                $("#tiposFinalidades").removeClass("invisivel");
                                carregarParcelasAjax($(this).val());
                        });
                });
                //contas
                if ($("#contasSelecionadas_"+idConta).is(':checked')){
                        selecionada =true;
                        $("#linhaConta_"+idConta+" img#ico-img").attr("src", "/portaltrtsp/images/subtracao-ico.png");
                        $("#tiposFinalidades").removeClass("invisivel");
                        carregarContasAjax(idConta);
                }
                //fechar contas ou parcelas nao selecionadas abertas
                if(!selecionada){
                        fecharConta(idConta);
                }
        }
        

        function selecionarConta(id){
            desmarcarParcelas(id);
            carregarContasAjax(id);
            atualizarValorTotalSelecionado();

            if(!$("#contasSelecionadas_" + id + ":checked").length) {
                desmarcaConta(id);
            } else if(typeof configurarTipoResgate == "function") {
                configurarTipoResgate();
            }

        }

        function selecionarContaComParcelaSelecionada(){
                $("#contas_processo").find("input:checked[type=checkbox][id^=parcelasSelecionadas_]").each(function(){
                        var id =  $(this).closest('table').prop('id');
                        var reg = /[0-9]+/;
                        var idConta = reg.exec(id);
                        $("#contasSelecionadas_"+idConta).prop('checked',true);
                        desmarcarParcelas(idConta);
                });
		atualizarValorTotalSelecionado();
        }

        function marcaParcelas(id){
                var marcarParcela;
                if($("#contasSelecionadas_"+id).is(':checked')){
                        marcarParcela = true;
                } else {
                        marcarParcela = false;
                }
                $("#tbSolicitacoes").find("input[id^=parcelasSelecionadas_"+id+"]").each(function(){
                        if (marcarParcela) {
                                carregarParcelasAjax($(this).val());
                        }
                        $(this).prop('checked', marcarParcela);
                });
        }

        function desmarcarParcelas(idConta) {
            $("#tbSolicitacoes").find("input[id^=parcelasSelecionadas_"+idConta+"]").each(function(){
                $(this).prop('checked', false);
            });
        }

        function selecionarParcela(idConta, idParcela){
                desmarcaConta(idConta);

                if ($("#parcelasSelecionadas_"+idConta+"_"+idParcela).is(':checked')) {
                    carregarParcelasAjax(idParcela);
                }
        }

        function desmarcaConta(id){
                $("#contasSelecionadas_"+id).prop('checked',false);
                $("#cb_tipoResgate").val("").trigger("chosen:updated");
                if(typeof configurarTipoResgate == "function"){
                        configurarTipoResgate();
                }
        }

        function atualizarValorTotalSelecionado(){
                var valorTotalSelecionado = 0;
                $("#tbSolicitacoes").find("input:checked[type=checkbox]").each(function(){
                        var valorSaldoSelecionado = $(this).prop("saldo");
                        if(valorSaldoSelecionado !== null && valorSaldoSelecionado !== '' && valorSaldoSelecionado >= 0){
                                valorTotalSelecionado = valorTotalSelecionado + parseFloat(valorSaldoSelecionado);
                        }
                });
                if(valorTotalSelecionado<=0){
                        $("#tiposFinalidades").addClass("invisivel");
                }else{
                  //  alert("aqui!");
                        $("#tiposFinalidades").removeClass("invisivel");
                        //document.getElementById("trTipoFinalidade").style.visibility="visible";
                        //document.getElementById("tr_numero_precatorio").style.visibility="visible";
                }

                if(isNaN(valorTotalSelecionado)){ // se nao e numero.
                        valorTotalSelecionado = "Erro!";
                }else{
                        valorTotalSelecionado = valorTotalSelecionado.toFixed(2).toString().replace("\.",",");
                       valorTotalSelecionado = Valor(valorTotalSelecionado);
                        $("#valorTotalSelecionado").val(valorTotalSelecionado);
                }

                $("#tbSolicitacoes").find("#somaValorTotalSelecionado").eq(0).html(valorTotalSelecionado);
                if($("#cb_tipoResgate").val()==='RESGATE_VALOR_TOTAL'){
                        $("#valor_real").val($("#valorTotalSelecionado").val());
                }
        }

        function mostrarDetalhesVinculo(idConta,event) {
                event.stopPropagation();
                event.preventDefault();
                // realizar chamada WS para carregar linhas do extrato
                var url = "/portaltrtsp/pages/movimentacao/conta/detalharVinculo/pendente/"+idConta;
                if (url === null) {
                        return;
                }

                var detalhes_vinculo = $("#dialog_ajax");
                detalhes_vinculo.html("");

                $.get(url, function (data) {
                        detalhes_vinculo.append(data);

                        // exibe popup modal
                        $("#dialog_ajax").dialog("open");

                });

        }
        function recarregarSaldos(idConta,event){
                if(event.target.type !== "button") return;

                $("#bt_recarregar_contas").find('img').toggle();
                carregarContasAjax(idConta);

                $("#bt_recarregar_contas").find('img').toggle();
                event.preventDefault();
        }

        function abrirParcelasEvent(idConta,event){
                if(event.target.type === "checkbox"){
                        var css = $("#contaId_"+idConta).css("display");
                        if(css.indexOf("none") < 0){
                                 return;
                        }
                }

                if(event.target.type === "button") return;

                if(document.getElementById("contaId_"+idConta).style.display === 'none'){
                        abrirParcelas(idConta);
                        carregarContasAjax(idConta);
                        carregarTodasAsParcelasAjax(idConta,0);
                } else {
                        fecharConta(idConta);
                        atualizarValorTotalSelecionado();
                }

                return false;
        }

        function carregarTodasAsParcelasAjax(idConta, page) {
                $.ajax({
                        dataType: "json",
                        url: "/portaltrtsp/pages/relatorios/extrato/conta/obterSaldo/" + idConta + "/parcelas/"+page+"/"+3,
                        removeBloqueio: true,
                        success: function (data) {

                                var saldoParcelas = data;

                                if(saldoParcelas.emptyList === undefined ){
                                    configurarCarregamentoParcelas(saldoParcelas);
                                    //enquanto houver registros continuar a fazer consultar a prÃ³xima pÃ¡gina
                                    carregarTodasAsParcelasAjax(idConta, ++page);

                                } else {
                                    //pode interromper as chamadas
                                }
                        }

                });

        }

        function fecharConta(idConta){
                $("#contasSelecionadas_"+idConta).hide();
                $("input[id^=contasSelecionadas_"+idConta+"]").prop("checked",false);
                $("tr[id^=contaId_"+idConta).find("input:checked[type=checkbox][id^=parcelasSelecionadas_]").each(function(){
                     //$(this).prop('checked',false);
                });
                $("tr[id^=contaId_"+idConta+"]").hide();
                $("#linhaConta_"+idConta+" img#ico-img").attr("src", "/portaltrtsp/images/soma-ico.png");
                //$("#tiposFinalidades").addClass("invisivel");
        }

        function configurarCarregamentoParcelas(saldoParcelas){
                var quantidadeParcelasCarregadas = 0;

                $.each(saldoParcelas,function(i){
                        var idParcela = saldoParcelas[i].idParcela;
                        var idConta = saldoParcelas[i].idConta;
                        var codigoRetorno = saldoParcelas[i].codigoRetorno;
                        var ckParcela = $("#parcelasSelecionadas_"+idConta+"_"+idParcela);

                        if(codigoRetorno === '0'){
                                $("#td_saldo_parcela_depositado_"+idParcela).html( saldoParcelas[i].valorCapitalFormatado );
                                $("#td_saldo_parcela_agendado_"+idParcela).html( saldoParcelas[i].valorCapitalAgendadoFormatado );
                                $("#td_saldo_parcela_bloqueado_"+idParcela).html( saldoParcelas[i].valorCapitalBloqueadoFormatado );
                                $("#td_saldo_parcela_saldo_"+idParcela).html( saldoParcelas[i].valorSaldoCorrigidoFormatado );
                                ckParcela.prop("saldo", saldoParcelas[i].valorSaldoCorrigido);
//                                ckParcela.show();
                                quantidadeParcelasCarregadas = quantidadeParcelasCarregadas +1;
                        }else{
                                $("#td_saldo_parcela_depositado_"+idParcela).html(
                                        "<label style='color:tomato'>(Problema na integra\u00E7\u00E3o com BB)</label>"
                                );
                                $("#td_saldo_parcela_agendado_"+idParcela).html(
                                        "<label style='color:tomato'>(Problema na integra\u00E7\u00E3o com BB)</label>"
                                );
                                $("#td_saldo_parcela_bloqueado_"+idParcela).html(
                                        "<label style='color:tomato'>(Problema na integra\u00E7\u00E3o com BB)</label>"
                                );
                                $("#td_saldo_parcela_saldo_"+idParcela).html(
                                        "<label style='color:tomato'>(Problema na integra\u00E7\u00E3o com BB)</label>"
                                );

//                                ckParcela.remove();
                        }
                });

        }

        function carregarContasAjax(idConta){
                if ($("#td_saldo_corrigido_conta_"+idConta).html().indexOf("img")>-1) {

                        var ajaxCorrigido = $("#tribunais_ajaxGif").clone();
                        var ajaxAgendado = $("#tribunais_ajaxGif").clone();
                        var ajaxBloqueado = $("#tribunais_ajaxGif").clone();
                        var ajaxDisponivel = $("#tribunais_ajaxGif").clone();
                        var ajaxDepositado = $("#tribunais_ajaxGif").clone();

                        $("#td_saldo_corrigido_conta_"+idConta).html(ajaxCorrigido);
                        $("#td_valor_agendado_"+idConta).html(ajaxAgendado);
                        $("#td_valor_bloqueado_"+idConta).html(ajaxBloqueado);
                        $("#td_valor_disponivel_"+idConta).html(ajaxDisponivel);
                        $("#td_saldo_conta_"+idConta).html(ajaxDepositado);

                        ajaxCorrigido.show();
                        ajaxAgendado.show();
                        ajaxBloqueado.show();
                        ajaxDisponivel.show();
                        ajaxDepositado.show();

                        var ajaxReq = $.getJSON("/portaltrtsp/pages/relatorios/extrato/conta/obterSaldo/"+idConta, function(data) {
                                var codigoRetorno = data.codigoRetorno;
                                if(codigoRetorno === '666'){
                                        $("#td_saldo_corrigido_conta_"+idConta).html("<label id='problema_bb' style='color:tomato'>("+data.msgUsuario+")</label>");
                                        $("#td_saldo_conta_"+idConta).html("<label id='problema_bb' style='color:tomato'>("+data.msgUsuario+")</label>");
                                        $("#td_valor_agendado_"+idConta).html("<label id='problema_bb' style='color:tomato'>("+data.msgUsuario+")</label>");
                                        $("#td_valor_bloqueado_"+idConta).html("<label id='problema_bb' style='color:tomato'>("+data.msgUsuario+")</label>");
                                        $("#td_valor_disponivel_"+idConta).html("<label id='problema_bb' style='color:tomato'>("+data.msgUsuario+")</label>");

                                        $("#tabela_parcelas_conta_"+idConta).find("input[id^=td_saldo_]").html(
                                                "<label id='problema_bb' style='color:tomato'>("+data.msgUsuario+")</label>"
                                        );
                                }
                                if(codigoRetorno === '0'){
                                        $("#td_saldo_corrigido_conta_"+idConta).html( data.valorSaldoCorrigidoFormatado );
                                        $("#td_saldo_conta_"+idConta).html(data.valorDepositoOriginalFormatado);
                                        $("#td_valor_agendado_"+idConta).html(data.valorCapitalAgendadoFormatado);
                                        $("#td_valor_bloqueado_"+idConta).html(data.valorCapitalBloqueadoFormatado);
                                        $("#td_valor_disponivel_"+idConta).html(data.valorSaldoCorrigidoFormatado);
//                                        $("#contasSelecionadas_"+idConta).prop("saldo", data.valorSaldoConta);//saldo esta nas parcelas
                                        $("#contasSelecionadas_"+idConta).prop("saldo", data.valorSaldoCorrigido);
                                }else{
                                        $("#td_saldo_corrigido_conta_"+idConta).html(
                                                "<label id='problema_bb' style='color:tomato'>(Problema na integra\u00E7\u00E3o com BB)</label>"
                                        );
                                        $("#td_saldo_conta_"+idConta).html("<label id='problema_bb' style='color:tomato'>(Problema na integra\u00E7\u00E3o com BB)</label>");
                                        $("#td_valor_agendado_"+idConta).html("<label id='problema_bb' style='color:tomato'>(Problema na integra\u00E7\u00E3o com BB)</label>");
                                        $("#td_valor_bloqueado_"+idConta).html("<label id='problema_bb' style='color:tomato'>(Problema na integra\u00E7\u00E3o com BB)</label>");
                                        $("#td_valor_disponivel_"+idConta).html("<label id='problema_bb' style='color:tomato'>(Problema na integra\u00E7\u00E3o com BB)</label>");

                                        $("#tabela_parcelas_conta_"+idConta).find("input[id^=td_saldo_]").html(
                                                "<label id='problema_bb' style='color:tomato'>(Problema na integra\u00E7\u00E3o com BB)</label>"
                                        );
                                }
                        });

                        ajaxReq.error(function() {
                              
                                $("#contasSelecionadas_"+idConta).hide();
                                $("#td_saldo_corrigido_conta_"+idConta).html(
                                        "<label id='problema_bb' style='color:tomato'>(Problema na integra\u00E7\u00E3o com BB)</label>"
                                );

                                $("#tabela_parcelas_conta_"+idConta).find("input[id^=td_saldo_]").html(
                                        "<label id='problema_bb' style='color:tomato'>(Problema na integra\u00E7\u00E3o com BB)</label>"
                                );

                                $("#td_saldo_conta_"+idConta).html("<label id='problema_bb' style='color:tomato'>(Problema na integra\u00E7\u00E3o com BB)</label>");
                                $("#td_valor_agendado_"+idConta).html("<label id='problema_bb' style='color:tomato'>(Problema na integra\u00E7\u00E3o com BB)</label>");
                                $("#td_valor_bloqueado_"+idConta).html("<label id='problema_bb' style='color:tomato'>(Problema na integra\u00E7\u00E3o com BB)</label>");
                                $("#td_valor_disponivel_"+idConta).html("<label id='problema_bb' style='color:tomato'>(Problema na integra\u00E7\u00E3o com BB)</label>");
                        });
                }
        }

        function carregarParcelasAjax(idParcela){
                if ($("#td_saldo_parcela_saldo_"+idParcela).html().indexOf("img")>-1) {
                        $.ajax({
                                dataType: "json",
                                url: "/portaltrtsp/pages/relatorios/extrato/conta/obterSaldo/" + idParcela + "/parcela",
                                success: function(data){
                                        var saldoParcelas = data;
                                        configurarCarregamentoParcelas(saldoParcelas);
                                        atualizarValorTotalSelecionado();
                                }
                        });
                }
        }

        function abrirParcelas(idConta) {
                $("#contasSelecionadas_"+idConta).show();
                $("#bloqueio").addClass("escurecer");
                var css = $("#contaId_"+idConta).css("display");

                esconderExibirListaParcelas(idConta);
                $("#linhaConta_"+idConta+" #ico-img").attr("src", "/portaltrtsp/images/subtracao-ico.png");
                $("#bloqueio").removeClass("escurecer");
        }

        function esconderExibirListaParcelas(idConta){
            // esconde ou exibe a lista de parcelas
                if(navigator.appName === "Microsoft Internet Explorer") {
                        if($("#contaId_"+idConta).is(":visible")){//IE8 always evaluates to true.
                             $("#contaId_"+idConta).hide();
                        }else{
                             $("#contaId_"+idConta).show();
                        }
                }else{
                    $("#contaId_"+idConta).fadeToggle("fast",function(){
                            if(!$("#contaId_"+idConta).is(":visible")){
                                    $("#tbSolicitacoes").find("input[id^=parcelasSelecionadas_"+idConta+"]").each(function(){
                                        $(this).prop("checked",false);
                                    });
                                    $("#contasSelecionadas_"+idConta).prop("checked",false);
                                    atualizarValorTotalSelecionado();
                            }
                    });
                }

        }
</script>
        
        
        <div id="campos_obrigatorios" class="invisivel">
                <p>Preencha todos os campos obrigatórios</p>
        </div>
        
        
                <table id="tiposFinalidades" class="formulario">
                        <tbody id="tbodyFormAlvara">
                           
                                <tr id="trTipoFinalidade">                                  
                                        <td class="titulo">Tipo de Finalidade*</td>
                                        <td>
                                            <select id="cb_tipoFinalidade" name="tipoFinalidade" style="min-width: 100px; display: none;" onchange="abrirLinhasFinalidades();">
                                                        <option value="">Selecione...</option>
                                                        <option value="SAQUE_AGENCIA_BB">Comparecer ao Banco</option><option value="CREDITO_CONTA_BB">Crédito em Conta no Banco do Brasil</option><option value="CREDITO_CONTA_OUTRO_BANCO">Crédito em Conta para Outros Bancos</option><option value="PIX">Pix</option><option value="PAGAMENTO_GUIA">Pagamento de Guia</option><option value="TED_JUDICIAL">TED Judicial</option><option value="DARF">Pagamento de DARF</option><option value="GRU">Pagamento de GRU</option><option value="GPS">Pagamento de GPS</option><option value="NOVO_DEPOSITO">Novo Depósito Judicial</option>								
                                                </select><div class="chosen-container chosen-container-single" style="width: 280px;" title="" id="cb_tipoFinalidade_chosen"><a class="chosen-single" tabindex="-1"><span>Pagamento de DARF</span><div><b></b></div></a><div class="chosen-drop"><div class="chosen-search"><input type="text" autocomplete="off"></div><ul class="chosen-results"><li class="active-result result-selected" style="" data-option-array-index="0">Selecione...</li><li class="active-result" style="" data-option-array-index="1">Comparecer ao Banco</li><li class="active-result" style="" data-option-array-index="2">Crédito em Conta no Banco do Brasil</li><li class="active-result" style="" data-option-array-index="3">Crédito em Conta para Outros Bancos</li><li class="active-result" style="" data-option-array-index="4">Pix</li><li class="active-result" style="" data-option-array-index="5">Pagamento de Guia</li><li class="active-result" style="" data-option-array-index="6">TED Judicial</li><li class="active-result result-selected" style="" data-option-array-index="7">Pagamento de DARF</li><li class="active-result" style="" data-option-array-index="8">Pagamento de GRU</li><li class="active-result" style="" data-option-array-index="9">Pagamento de GPS</li><li class="active-result" style="" data-option-array-index="10">Novo Depósito Judicial</li></ul></div></div>
                                                <span id="cb_tipoFinalidade_errors" class="invisivel">Campo obrigatorio</span>
                                                
                                        </td>
                                </tr>
                        
                                
                                        
                                        
                                        
                                        
                                                



























<!-- Formulario de selecao de autor e reu

OBS: Passar o nome da classe via jsp:param.
-->

<tr id="linhaTipoBeneficiario" class="finalidade_darf">
        <td class="titulo">Tipo de Contribuinte*</td>
        <td>
            <input type="hidden" id="beneficiario_id" name="beneficiario.id" value="0">
            <input type="hidden" id="beneficiario_pessoa_nome" name="beneficiario.pessoa.nome" value="HOSPITAL E MATERNIDADE VIDA">
            <input type="hidden" id="beneficiario_pessoa_cpfCnpj" name="beneficiario.pessoa.cpfCnpj" value="96534300000120">
            <input type="hidden" id="beneficiario_parte_principal" name="beneficiario.pessoa.principal" value="">
            <input type="hidden" id="beneficiario_papel" name="beneficiario.papel" value="">
            <input type="hidden" id="beneficiario_processo" name="beneficiario.processo.id" value="11073364">
            
            <div id="camposBeneficiario">    <input type="hidden" id="96534300000120" value="96534300000120;HOSPITAL E MATERNIDADE VIDA" s="" ltda.;false;reclamado'=""><input type="hidden" id="67839969000121" value="67839969000121;AMEPLAN ASSISTENCIA MEDICA PLANEJADA LTDA.;false;RECLAMADO"><input type="hidden" id="07273957000150" value="07273957000150;CLINICA DE ESPECIALIDADE PARANAGUA LTDA;false;RECLAMADO"><input type="hidden" id="09338791000139" value="09338791000139;COMPLEXO HOSPITALAR J.S.J LTDA - EM RECUPERACAO JUDICIAL;false;RECLAMADO"><input type="hidden" id="06330689000107" value="06330689000107;PRONTO ATENDIMENTO SUPREMO LTDA;false;RECLAMADO"><input type="hidden" id="23642793000148" value="23642793000148;BETA SAUDE E PARTICIPACOES LTDA - EM RECUPERACAO JUDICIAL;false;RECLAMADO"><input type="hidden" id="96534300000120" value="96534300000120;HOSPITAL E MATERNIDADE VIDA" s="" ltda.;false;reclamado'=""><input type="hidden" id="67839969000121" value="67839969000121;AMEPLAN ASSISTENCIA MEDICA PLANEJADA LTDA.;false;RECLAMADO"><input type="hidden" id="07273957000150" value="07273957000150;CLINICA DE ESPECIALIDADE PARANAGUA LTDA;false;RECLAMADO"><input type="hidden" id="09338791000139" value="09338791000139;COMPLEXO HOSPITALAR J.S.J LTDA - EM RECUPERACAO JUDICIAL;false;RECLAMADO"><input type="hidden" id="06330689000107" value="06330689000107;PRONTO ATENDIMENTO SUPREMO LTDA;false;RECLAMADO"><input type="hidden" id="23642793000148" value="23642793000148;BETA SAUDE E PARTICIPACOES LTDA - EM RECUPERACAO JUDICIAL;false;RECLAMADO"></div>
            
        <select id="cb_tipoBeneficiario" name="tipoBeneficiario" style="min-width: 150px; display: none;" onchange="cbTipoBeneficiarioChange()">
			<option value="">Selecione...</option>
                        
                                <option value="10" papel="ADV_RECLAMADO" tipo="ADVOGADO">Adv Réu</option>
                        
                                <option value="9" papel="ADV_RECLAMANTE" tipo="ADVOGADO">Adv Autor</option>
                        
                                <option value="5" papel="RECLAMADO" tipo="REU">Réu</option>
                        
                                <option value="1" papel="RECLAMANTE" tipo="AUTOR">Autor</option>
                        
                                <option value="11" papel="TERCEIRO" tipo="OUTROS">Terceiro</option>
                        
		</select><div class="chosen-container chosen-container-single" style="width: 203px;" title="" id="cb_tipoBeneficiario_chosen"><a class="chosen-single" tabindex="-1"><span>Réu</span><div><b></b></div></a><div class="chosen-drop"><div class="chosen-search"><input type="text" autocomplete="off"></div><ul class="chosen-results"><li class="active-result result-selected" style="" data-option-array-index="0">Selecione...</li><li class="active-result" style="" data-option-array-index="1">Adv Réu</li><li class="active-result" style="" data-option-array-index="2">Adv Autor</li><li class="active-result result-selected" style="" data-option-array-index="3">Réu</li><li class="active-result" style="" data-option-array-index="4">Autor</li><li class="active-result" style="" data-option-array-index="5">Terceiro</li></ul></div></div>
                <input type="hidden" id="beneficiarioTransiente">
                <input type="hidden" id="beneficiario" name="beneficiario.id" value="">
                <span id="cb_tipoBeneficiario_errors" class="invisivel">Campo obrigatorio</span>
                  
                <input type="hidden" id="qtdeBeneficiarios" name="qtdeBeneficiarios">
        </td>
</tr>
<tr id="linhaBeneficiario" style="" class="finalidade_darf">
        
        <td class="titulo">
                Beneficiário*
        </td>
        <td id="colunaBeneficiario">
        	<div id="divBeneficiario">
	            <select id="comboBeneficiario" onchange="verificarBeneficiarioSelecionado();setarHiddens(this.value)" style="display: none;"><option value="0" selected="selected">Selecione...</option><option value="96534300000120" cpf="96534300000120">HOSPITAL E MATERNIDADE VIDA'S LTDA. </option><option value="67839969000121" cpf="67839969000121">AMEPLAN ASSISTENCIA MEDICA PLANEJADA LTDA. </option><option value="07273957000150" cpf="07273957000150">CLINICA DE ESPECIALIDADE PARANAGUA LTDA </option><option value="09338791000139" cpf="09338791000139">COMPLEXO HOSPITALAR J.S.J LTDA - EM RECUPERACAO JUDICIAL </option><option value="06330689000107" cpf="06330689000107">PRONTO ATENDIMENTO SUPREMO LTDA </option><option value="23642793000148" cpf="23642793000148">BETA SAUDE E PARTICIPACOES LTDA - EM RECUPERACAO JUDICIAL </option></select><div class="chosen-container chosen-container-single" style="width: 450px; display: inline-block;" title="" id="comboBeneficiario_chosen"><a class="chosen-single" tabindex="-1"><span>HOSPITAL E MATERNIDADE VIDA'S LTDA.</span><div><b></b></div></a><div class="chosen-drop"><div class="chosen-search"><input type="text" autocomplete="off"></div><ul class="chosen-results"><li class="active-result" style="" data-option-array-index="0">Selecione...</li><li class="active-result result-selected" style="" data-option-array-index="1">HOSPITAL E MATERNIDADE VIDA'S LTDA. </li><li class="active-result" style="" data-option-array-index="2">AMEPLAN ASSISTENCIA MEDICA PLANEJADA LTDA. </li><li class="active-result" style="" data-option-array-index="3">CLINICA DE ESPECIALIDADE PARANAGUA LTDA </li><li class="active-result" style="" data-option-array-index="4">COMPLEXO HOSPITALAR J.S.J LTDA - EM RECUPERACAO JUDICIAL </li><li class="active-result" style="" data-option-array-index="5">PRONTO ATENDIMENTO SUPREMO LTDA </li><li class="active-result" style="" data-option-array-index="6">BETA SAUDE E PARTICIPACOES LTDA - EM RECUPERACAO JUDICIAL </li></ul></div></div>   
	            
            </div>
        </td>
</tr>
<tr id="linha_beneficiario_cpfCnpj" class="finalidade_darf" style="opacity: 1; display: table-row;">
        <td id="tituloBeneficiario_cpfCnpj" class="titulo">
                
                        
                        
                             CPF/CNPJ do Contribuinte
                        
                
                









<span title="Preencha o CPF ou CNPJ sem formatação." class="bt-acao-ajuda"> </span>
        </td>
        <td>
		

































        
        
<div style="float:left">
	<input id="solicitacaoTransiente_beneficiario_pessoa_cpfCnpj" name="solicitacaoTransiente.beneficiario.pessoa.cpfCnpj" onkeydown="Mascara(this,CpfCnpjContagem);" onblur="validaCpfCnpj_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj();byPassCpfCnpjBeneficiarioConta();" onchange="Mascara(this,CpfCnpjContagem);" type="text" value="" size="40" maxlength="18">
	





















<input type="button" id="solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button" class="botaoAtualizar invisivel" value="Validar" onclick="executarAcao_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button()">

<script type="text/javascript">

	function executarAcao_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button(){
				
                
	            var retorno = true;

                
                        retorno = validaCpfCnpj_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj();
                
        
                
                        
                if(retorno) {
                        
                }
	}
</script>

	<span id="span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj" class="fieldWithErrors invisible"></span>
	
        <br>
        <label id="lb_msg_cpf_cnpj_quantidade_digitos" style="color:#555555; font-size:10px;">(Informe 11 (onze) digitos para CPF ou 14 (quatorze) para CNPJ)</label>
</div>
<script type="text/javascript">
function validaCpfCnpj_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj() {
        $("#solicitacaoTransiente_beneficiario_pessoa_nome").val("");
	var cpfCnpj = Integer($("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val());
	cpfCnpj = cpfCnpj.replace(/[-./]/g, '');
	if(cpfCnpj == "") {
		
		    $("#solicitacaoTransiente_beneficiario_pessoa_nome").val("");
		    
		    
		    
		    $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('invisible');
		    $("#tribunais_ajaxGif_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button").hide();
		    $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button").removeAttr("disabled");
		
		return true;
	}

	if("CPFCNPJ" === 'CPFCNPJ'){

		if($("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val().length!=14 && $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val().length!=18){
		            aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	if("CPFCNPJ" === 'CPF'){

		if($("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val().length!=14){
		            aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	if("CPFCNPJ" === 'CNPJ'){

		if($("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val().length!=18){
		            aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	
	$("#tribunais_ajaxGif_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button").show();
		
	// realiza chamada WS
	$("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").trigger("eventIniciarRequisicaoAjax");
        
        
        //validar cpfcnpj nas partes do processo e no bb ou somento no bb
        if(true){
                var opt = $("#cb_tipoBeneficiario > option:checked");
                var tipo = opt.attr('tipo');
                var url = "/portaltrtsp/pages/processo/tribunal/"+$("#numeroProcesso").val()+"/cpfcnpj/"+cpfCnpj+"/"+tipo+"/validar.json";
        }else{      
                var url = "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validarModulo.json";
                
                        url = "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validar.json";
                
        }
        
        var ajaxReq = $.ajax(url, {
                dataType: "text",

                statusCode: {
                        200: function() { 
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldWithErrors');
                                aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("");
                                   
                        },
                        204: function() { 
                                aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("O CPF/CNPJ inválido ou formato incorreto."); 
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('fieldWithErrors');
                        },
                        404: function() { 
                                aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("Serviço WS para acessos externos não encontrado."); 
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('fieldWithErrors');
                        },
                        406: function() { 
                                aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("A consulta processual não retornou dados do CPF/CNPJ da parte informada."); 
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('fieldWithErrors');
                        },
                        500: function() { 
                                aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("Serviço externo indisponível. Tente novamente mais tarde."); 
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('fieldWithErrors');
                        },
                        503: function() { 
                                aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("Serviço externo indisponível. Tente novamente mais tarde."); 
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('fieldWithErrors');
                        },
                        666: function(xhr) { 
                               console.log(xhr.responseText);
                              $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldSuccess');
                              $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldWithErrors');
                              $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('invisible');	
                              $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('fieldWithErrors');
                              aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj(xhr.responseText);                        
                        }
                },

                
                        success: function(data, textStatus, jqXHR) {
                                $("#solicitacaoTransiente_beneficiario_pessoa_nome").val(data);
                                
                },
                

                complete: function() {
                    $("#tribunais_ajaxGif_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button").hide();
                    $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button").removeAttr("disabled");

                    
                        $("#solicitacaoTransiente_beneficiario_pessoa_nome\\.errors").hide();
                    

                    $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").trigger("eventFinalizarRequisicaoAjax");
                }
        });
	
	return true;
}

function aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj(validacaoMsg) {
	if(validacaoMsg != ""){
		$("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('invisible');	
	}else{
		$("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('invisible');
	}
    $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").html(validacaoMsg);
    
    
	    if(validacaoMsg == "") {
			$("#solicitacaoTransiente_beneficiario_pessoa_nome").attr("readonly", "readonly");
	    } else {
	    			
	    }
    
    
//    if(document.getElementById('cb_tipoFinalidade') != null){
//        var tp_finalidade = document.getElementById('cb_tipoFinalidade').value;
//        console.log("finalidade <:> " + tp_finalidade );
//        if(tp_finalidade === "PIX"){
//           //  this.montaComboTitularConta();
//            // window.addEventListener("load", function(){
//                    montaComboTitularConta(); 
//            //    });
//         }
//     }  
}



</script>
	</td>
</tr>

<tr id="linha_beneficiario_nome" class="finalidade_darf" style="opacity: 1; display: none;">
    <td id="tituloBeneficiario_nome" class="titulo">
            
                    
                    
                         Nome do Contribuinte
                    
            
    </td>
    <td>
        <input id="solicitacaoTransiente_beneficiario_pessoa_nome" name="solicitacaoTransiente.beneficiario.pessoa.nome" readonly="readonly" type="text" value="" size="45" maxlength="100">
        
    </td>
</tr>




    
    <tr id="selecao_tipoBeneficiario" class="finalidade_darf invisivel">
            <td class="titulo">Procurador / Representante Legal</td>
            <td>
                    <input id="rb_procurador" name="representantes" type="checkbox" value="PROCURADOR"><input type="hidden" name="_representantes" value="on">
                    Procurador
                    <input id="rb_representanteLegal" name="representantes" type="checkbox" value="REPRESENTANTE_LEGAL"><input type="hidden" name="_representantes" value="on">
                    Representante Legal

                    
            </td>
    </tr>

    <tr id="linha_procurador_cpfCnpj" class="finalidade_darf" style="display: none !important;">
                <td class="titulo">
                    CPF/CNPJ Procurador*
                    









<span title="Preencha o CPF ou CNPJ sem formatação." class="bt-acao-ajuda"> </span>
                </td>
                <td>
                        

































        
        
<div style="float:left">
	<input id="solicitacaoTransiente_procurador_cpfCnpj" name="solicitacaoTransiente.procurador.cpfCnpj" onkeydown="Mascara(this,CpfCnpjContagem);" onblur="montaComboTitularContaPIX()" onchange="Mascara(this,CpfCnpjContagem);" type="text" value="" size="40" maxlength="18">
	





















<input type="button" id="solicitacaoTransiente_procurador_cpfCnpj_button" class="botaoAtualizar invisivel" value="Validar" onclick="executarAcao_solicitacaoTransiente_procurador_cpfCnpj_button()">

<script type="text/javascript">

	function executarAcao_solicitacaoTransiente_procurador_cpfCnpj_button(){
				
                
	            var retorno = true;

                
                        retorno = validaCpfCnpj_solicitacaoTransiente_procurador_cpfCnpj();
                
        
                
                        
                if(retorno) {
                        
                }
	}
</script>

	<span id="span_solicitacaoTransiente_procurador_cpfCnpj" class="fieldWithErrors invisible"></span>
	
        <br>
        <label id="lb_msg_cpf_cnpj_quantidade_digitos" style="color:#555555; font-size:10px;">(Informe 11 (onze) digitos para CPF ou 14 (quatorze) para CNPJ)</label>
</div>
<script type="text/javascript">
function validaCpfCnpj_solicitacaoTransiente_procurador_cpfCnpj() {
        $("#solicitacaoTransiente\\.procurador\\.nome").val("");
	var cpfCnpj = Integer($("#solicitacaoTransiente_procurador_cpfCnpj").val());
	cpfCnpj = cpfCnpj.replace(/[-./]/g, '');
	if(cpfCnpj == "") {
		
		    $("#solicitacaoTransiente\\.procurador\\.nome").val("");
		    
		    
		    
		    $("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('invisible');
		    $("#tribunais_ajaxGif_solicitacaoTransiente_procurador_cpfCnpj_button").hide();
		    $("#solicitacaoTransiente_procurador_cpfCnpj_button").removeAttr("disabled");
		
		return true;
	}

	if("CPFCNPJ" === 'CPFCNPJ'){

		if($("#solicitacaoTransiente_procurador_cpfCnpj").val().length!=14 && $("#solicitacaoTransiente_procurador_cpfCnpj").val().length!=18){
		            aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	if("CPFCNPJ" === 'CPF'){

		if($("#solicitacaoTransiente_procurador_cpfCnpj").val().length!=14){
		            aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	if("CPFCNPJ" === 'CNPJ'){

		if($("#solicitacaoTransiente_procurador_cpfCnpj").val().length!=18){
		            aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	
	$("#tribunais_ajaxGif_solicitacaoTransiente_procurador_cpfCnpj_button").show();
		
	// realiza chamada WS
	$("#solicitacaoTransiente_procurador_cpfCnpj").trigger("eventIniciarRequisicaoAjax");
        
        
        //validar cpfcnpj nas partes do processo e no bb ou somento no bb
        if(false){
                var opt = $("#cb_tipoBeneficiario > option:checked");
                var tipo = opt.attr('tipo');
                var url = "/portaltrtsp/pages/processo/tribunal/"+$("#numeroProcesso").val()+"/cpfcnpj/"+cpfCnpj+"/"+tipo+"/validar.json";
        }else{      
                var url = "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validarModulo.json";
                
                        url = "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validar.json";
                
        }
        
        var ajaxReq = $.ajax(url, {
                dataType: "text",

                statusCode: {
                        200: function() { 
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldWithErrors');
                                aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("");
                                   
                        },
                        204: function() { 
                                aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("O CPF/CNPJ inválido ou formato incorreto."); 
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('fieldWithErrors');
                        },
                        404: function() { 
                                aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("Serviço WS para acessos externos não encontrado."); 
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('fieldWithErrors');
                        },
                        406: function() { 
                                aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("A consulta processual não retornou dados do CPF/CNPJ da parte informada."); 
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('fieldWithErrors');
                        },
                        500: function() { 
                                aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("Serviço externo indisponível. Tente novamente mais tarde."); 
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('fieldWithErrors');
                        },
                        503: function() { 
                                aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("Serviço externo indisponível. Tente novamente mais tarde."); 
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('fieldWithErrors');
                        },
                        666: function(xhr) { 
                               console.log(xhr.responseText);
                              $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldSuccess');
                              $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldWithErrors');
                              $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('invisible');	
                              $("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('fieldWithErrors');
                              aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj(xhr.responseText);                        
                        }
                },

                
                        success: function(data, textStatus, jqXHR) {
                                $("#solicitacaoTransiente\\.procurador\\.nome").val(data);
                                
                },
                

                complete: function() {
                    $("#tribunais_ajaxGif_solicitacaoTransiente_procurador_cpfCnpj_button").hide();
                    $("#solicitacaoTransiente_procurador_cpfCnpj_button").removeAttr("disabled");

                    
                        $("#solicitacaoTransiente\\.procurador\\.nome\\.errors").hide();
                    

                    $("#solicitacaoTransiente_procurador_cpfCnpj").trigger("eventFinalizarRequisicaoAjax");
                }
        });
	
	return true;
}

function aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj(validacaoMsg) {
	if(validacaoMsg != ""){
		$("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('invisible');	
	}else{
		$("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('invisible');
	}
    $("#span_solicitacaoTransiente_procurador_cpfCnpj").html(validacaoMsg);
    
    
	    if(validacaoMsg == "") {
			$("#solicitacaoTransiente\\.procurador\\.nome").attr("readonly", "readonly");
	    } else {
	    			
	    }
    
    
//    if(document.getElementById('cb_tipoFinalidade') != null){
//        var tp_finalidade = document.getElementById('cb_tipoFinalidade').value;
//        console.log("finalidade <:> " + tp_finalidade );
//        if(tp_finalidade === "PIX"){
//           //  this.montaComboTitularConta();
//            // window.addEventListener("load", function(){
//                    montaComboTitularConta(); 
//            //    });
//         }
//     }  
}



</script>
                </td>
        </tr>
        <tr id="linha_procurador_nome" class="finalidade_darf" style="display: none !important;">
                <td class="titulo">Nome Procurador*</td>
                <td>
                        <input id="solicitacaoTransiente.procurador.nome" name="solicitacaoTransiente.procurador.nome" onchange="carregarListaPix()" type="text" value="" size="45" maxlength="100">
                        
                </td>
        </tr>
        <tr id="linha_procurador_registroOAB" class="finalidade_darf" style="display: none !important;">
                <td class="titulo">N° Registro OAB*</td>
                <td>
                        <input id="solicitacaoTransiente.numeroRegistroOab" name="solicitacaoTransiente.numeroRegistroOab" type="text" value="" size="10" maxlength="10">
                        
                </td>
        </tr>
        <tr id="linha_procurador_ufOAB" class="finalidade_darf" style="display: none !important;">
                <td class="titulo">
                        UF OAB*
                </td>   
                <td>
                        <select id="cb_estados" name="solicitacaoTransiente.estado" style="min-width:150px;">
                                <option value="" selected="selected">Selecione...</option>
                                
                        </select>
                        
                </td>
        </tr>
        <tr id="linha_procurador_tipoOAB" class="finalidade_darf" style="display: none !important;">
                <td class="titulo">
                        Tipo OAB*
                </td>
                <td>
                        <input id="solicitacaoTransiente.tipoRegistroOab" name="solicitacaoTransiente.tipoRegistroOab" type="text" value="" size="20" maxlength="20">
                        

                </td>
        </tr>

    <tr id="linha_representanteLegal_cpfCnpj" class="finalidade_darf" style="display: none !important;">
                <td class="titulo">
                    CPF/CNPJ Representante Legal*
                    









<span title="Preencha o CPF ou CNPJ sem formatação." class="bt-acao-ajuda"> </span>
                </td>
                <td>
                        

































        
        
<div style="float:left">
	<input id="solicitacaoTransiente_representanteLegal_cpfCnpj" name="solicitacaoTransiente.representanteLegal.cpfCnpj" onkeydown="Mascara(this,CpfCnpjContagem);" onblur="montaComboTitularContaPIX()" onchange="Mascara(this,CpfCnpjContagem);" type="text" value="" size="40" maxlength="18">
	





















<input type="button" id="solicitacaoTransiente_representanteLegal_cpfCnpj_button" class="botaoAtualizar invisivel" value="Validar" onclick="executarAcao_solicitacaoTransiente_representanteLegal_cpfCnpj_button()">

<script type="text/javascript">

	function executarAcao_solicitacaoTransiente_representanteLegal_cpfCnpj_button(){
				
                
	            var retorno = true;

                
                        retorno = validaCpfCnpj_solicitacaoTransiente_representanteLegal_cpfCnpj();
                
        
                
                        
                if(retorno) {
                        
                }
	}
</script>

	<span id="span_solicitacaoTransiente_representanteLegal_cpfCnpj" class="fieldWithErrors invisible"></span>
	
        <br>
        <label id="lb_msg_cpf_cnpj_quantidade_digitos" style="color:#555555; font-size:10px;">(Informe 11 (onze) digitos para CPF ou 14 (quatorze) para CNPJ)</label>
</div>
<script type="text/javascript">
function validaCpfCnpj_solicitacaoTransiente_representanteLegal_cpfCnpj() {
        $("#solicitacaoTransiente\\.representanteLegal\\.nome").val("");
	var cpfCnpj = Integer($("#solicitacaoTransiente_representanteLegal_cpfCnpj").val());
	cpfCnpj = cpfCnpj.replace(/[-./]/g, '');
	if(cpfCnpj == "") {
		
		    $("#solicitacaoTransiente\\.representanteLegal\\.nome").val("");
		    
		    
		    
		    $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('invisible');
		    $("#tribunais_ajaxGif_solicitacaoTransiente_representanteLegal_cpfCnpj_button").hide();
		    $("#solicitacaoTransiente_representanteLegal_cpfCnpj_button").removeAttr("disabled");
		
		return true;
	}

	if("CPFCNPJ" === 'CPFCNPJ'){

		if($("#solicitacaoTransiente_representanteLegal_cpfCnpj").val().length!=14 && $("#solicitacaoTransiente_representanteLegal_cpfCnpj").val().length!=18){
		            aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	if("CPFCNPJ" === 'CPF'){

		if($("#solicitacaoTransiente_representanteLegal_cpfCnpj").val().length!=14){
		            aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	if("CPFCNPJ" === 'CNPJ'){

		if($("#solicitacaoTransiente_representanteLegal_cpfCnpj").val().length!=18){
		            aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	
	$("#tribunais_ajaxGif_solicitacaoTransiente_representanteLegal_cpfCnpj_button").show();
		
	// realiza chamada WS
	$("#solicitacaoTransiente_representanteLegal_cpfCnpj").trigger("eventIniciarRequisicaoAjax");
        
        
        //validar cpfcnpj nas partes do processo e no bb ou somento no bb
        if(false){
                var opt = $("#cb_tipoBeneficiario > option:checked");
                var tipo = opt.attr('tipo');
                var url = "/portaltrtsp/pages/processo/tribunal/"+$("#numeroProcesso").val()+"/cpfcnpj/"+cpfCnpj+"/"+tipo+"/validar.json";
        }else{      
                var url = "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validarModulo.json";
                
                        url = "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validar.json";
                
        }
        
        var ajaxReq = $.ajax(url, {
                dataType: "text",

                statusCode: {
                        200: function() { 
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldWithErrors');
                                aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("");
                                   
                        },
                        204: function() { 
                                aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("O CPF/CNPJ inválido ou formato incorreto."); 
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('fieldWithErrors');
                        },
                        404: function() { 
                                aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("Serviço WS para acessos externos não encontrado."); 
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('fieldWithErrors');
                        },
                        406: function() { 
                                aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("A consulta processual não retornou dados do CPF/CNPJ da parte informada."); 
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('fieldWithErrors');
                        },
                        500: function() { 
                                aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("Serviço externo indisponível. Tente novamente mais tarde."); 
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('fieldWithErrors');
                        },
                        503: function() { 
                                aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("Serviço externo indisponível. Tente novamente mais tarde."); 
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('fieldWithErrors');
                        },
                        666: function(xhr) { 
                               console.log(xhr.responseText);
                              $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldSuccess');
                              $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldWithErrors');
                              $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('invisible');	
                              $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('fieldWithErrors');
                              aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj(xhr.responseText);                        
                        }
                },

                
                        success: function(data, textStatus, jqXHR) {
                                $("#solicitacaoTransiente\\.representanteLegal\\.nome").val(data);
                                
                },
                

                complete: function() {
                    $("#tribunais_ajaxGif_solicitacaoTransiente_representanteLegal_cpfCnpj_button").hide();
                    $("#solicitacaoTransiente_representanteLegal_cpfCnpj_button").removeAttr("disabled");

                    
                        $("#solicitacaoTransiente\\.representanteLegal\\.nome\\.errors").hide();
                    

                    $("#solicitacaoTransiente_representanteLegal_cpfCnpj").trigger("eventFinalizarRequisicaoAjax");
                }
        });
	
	return true;
}

function aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj(validacaoMsg) {
	if(validacaoMsg != ""){
		$("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('invisible');	
	}else{
		$("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('invisible');
	}
    $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").html(validacaoMsg);
    
    
	    if(validacaoMsg == "") {
			$("#solicitacaoTransiente\\.representanteLegal\\.nome").attr("readonly", "readonly");
	    } else {
	    			
	    }
    
    
//    if(document.getElementById('cb_tipoFinalidade') != null){
//        var tp_finalidade = document.getElementById('cb_tipoFinalidade').value;
//        console.log("finalidade <:> " + tp_finalidade );
//        if(tp_finalidade === "PIX"){
//           //  this.montaComboTitularConta();
//            // window.addEventListener("load", function(){
//                    montaComboTitularConta(); 
//            //    });
//         }
//     }  
}



</script>
                </td>
        </tr>
        <tr id="linha_representanteLegal_nome" class="finalidade_darf" style="display: none !important;">
                <td class="titulo">Nome Representante Legal*</td>
                <td>
                        <input id="solicitacaoTransiente.representanteLegal.nome" name="solicitacaoTransiente.representanteLegal.nome" onchange="carregarListaPix()" type="text" value="" size="45" maxlength="100">
                        
                </td>
        </tr>

    <tr id="linhaFolhaProcuracao" class="finalidade_darf" style="opacity: 1; display: none;">
            <td class="titulo">
                    Folha da Procuração
            </td>
            <td>
                    <input id="solicitacaoTransiente.folhaProcuracao" name="solicitacaoTransiente.folhaProcuracao" type="text" value="">
                    
            </td>
    </tr>

    
<script type="text/javascript">
    
    function carregarListaPix(){
        var combo = document.getElementById('pixDi1namico');

        if (combo !== null && combo !== undefined){ 
            for (a in combo.options) { combo.options.remove(a); }
        }

        var podeSelecionar = document.getElementById('rb_beneficiarioTitularContaFalse').checked;

        if(!podeSelecionar){
            $("#linhaChavePixDinamico").fadeOut();
            $("#linhaChavePixCpfCnpjBeneficiario").fadeIn();
            
            var cpfCnpj = $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val();
            var nome = $("#solicitacaoTransiente_beneficiario_pessoa_nome").val();

            preecherCamposCpfCnpjNomeFinalidadePIX(cpfCnpj, nome);
            
            return;
                
        }
        
        $("#linhaChavePixDinamico").fadeIn();
        $("#linhaChavePixCpfCnpjBeneficiario").fadeOut();

        var beneficiario = document.getElementById('solicitacaoTransiente_beneficiario_pessoa_cpfCnpj').value;

        var procurador = document.getElementById('solicitacaoTransiente_procurador_cpfCnpj').value;

        var representante = document.getElementById('solicitacaoTransiente_representanteLegal_cpfCnpj').value;



        combo.appendChild(new Option('Selecione','selecione'));
        
        if(beneficiario !== null && beneficiario.trim().length !== 0){
            combo.appendChild(new Option(beneficiario,beneficiario));
        }

        if(procurador !== null && procurador.trim().length !== 0){
            combo.appendChild(new Option(procurador,procurador));
        }
        
        if(representante !== null && representante.trim().length !== 0){
            combo.appendChild(new Option(representante,representante));
        }
        
        
        combo.addEventListener('change', function handle(event){
            var selectElement = event.target;
            var value = selectElement.value;    
            
            
            var value2 = combo.options[combo.selectedIndex].value;
            var text2 = combo.options[combo.selectedIndex].text;
            
            preecherCamposCpfCnpjNomeFinalidadePIX(value2, text2);
            
        });
    }
    
        var finalidade = document.getElementById('cb_tipoFinalidade').value;
        
        if (finalidade === "CREDITO_CONTA_BB" || finalidade === "CREDITO_CONTA_OUTRO_BANCO" || finalidade === "PIX") {
            document.getElementById('rb_beneficiarioTitularContaFalse').addEventListener('click', function(e){  
                limparCpfCnpjNomeFinalidade();
            });

            document.getElementById('rb_beneficiarioTitularContaTrue').addEventListener('click', function(e){  
                carregarCpfCnpjNomeBeneficiarioTitularConta(finalidade);
            });
        }
        
        $(document).ready(function(){
            var mensagemErro = document.getElementById('msgException');
            if (mensagemErro === undefined || mensagemErro === null) {
                $("#rb_representanteLegal").prop("checked", false);
                $("#rb_procurador").prop("checked", false);
                limparCamposProcurador();
                limparCamposRepresentanteLegal();
                ocultarConteudoBeneficiario();
                ocultarConteudoProcurador();
                ocultarConteudoRepresentanteLegal();
                verificarInclusaoCampoFolhaProcuracao();
                verificarFinalidadeCredito();
            }
            setTimeout(()=> {
                carregarTipoBeneficiario();
                reloadTipoBeneficiario();
                criarChanges();
                reloadRadioRepresentacao();
                $("#cb_tipoBeneficiario_chosen").css("width","203");
                $("#cb_tipoBeneficiario").trigger("chosen:updated");
                removerDuplicados();
                verificarMostrarTitular();
            }, 500);
        });
        
        function verificarMostrarTitular() {
            if($("#cb_tipoFinalidade").val() === "CREDITO_CONTA_OUTRO_BANCO"){
                var podeSelecionar = document.getElementById('rb_beneficiarioTitularContaTrue');
                if (podeSelecionar !== null && podeSelecionar !== undefined && podeSelecionar.checked) {
                    $("#cpf_cnpj_titular_finalidade_credito_outros_bancos").fadeOut();
                    $("#nome_titular_finalidade_credito_outros_bancos").fadeOut();
                    var linhaPix = document.getElementById("linhaChavePixCpfCnpjBeneficiario");
                    linhaPix.style.opacity = '1';
                    $("#linhaChavePixCpfCnpjBeneficiario").fadeIn();
                } else {
                    $("#linhaChavePixCpfCnpjBeneficiario").fadeOut();
                    $("#cpf_cnpj_titular_finalidade_credito_outros_bancos").fadeIn();
                    $("#nome_titular_finalidade_credito_outros_bancos").fadeIn();
                } 
            }
        }
        
        function verificarFinalidadeCredito() {
            if ($("#cb_tipoFinalidade").val() === "CREDITO_CONTA_BB" || $("#cb_tipoFinalidade").val() === "CREDITO_CONTA_OUTRO_BANCO" || $("#cb_tipoFinalidade").val() === "PIX") {
                $("#rb_beneficiarioTitularContaTrue").prop("checked", true);
            } else {
                $("#rb_beneficiarioTitularContaTrue").prop("checked", false);
            }
        }
        
        function beneficiarioEhTitularConta(){
            if ($("#cb_tipoFinalidade").val() === "CREDITO_CONTA_BB" || $("#cb_tipoFinalidade").val() === "CREDITO_CONTA_OUTRO_BANCO" || $("#cb_tipoFinalidade").val() === "PIX") {
                $("#rb_beneficiarioTitularContaTrue").prop("checked", true);
            } else {
                $("#rb_beneficiarioTitularContaTrue").prop("checked", false);
            }
        }
        
        function carregarCpfCnpjNomeBeneficiarioTitularConta() {
            var finalidade = document.getElementById('cb_tipoFinalidade').value;
            var tipoBeneficiario = document.getElementById('cb_tipoBeneficiario').value;

            if (finalidade === "PIX" && tipoBeneficiario !== "") {

                var cpfCnpj = "";
                var nome = "";
                var beneficiarioEhIgualTitularConta = $("#rb_beneficiarioTitularContaTrue").is(':checked');

                if (beneficiarioSelecionadoDoCombo && beneficiarioEhIgualTitularConta) {

                    cpfCnpj = recuperarCpfCnpjBeneficiarioSelecionadoComMascara();
                    nome = $("#comboBeneficiario option:selected").text();
                }

                if (beneficiarioDigitadoManualmente && beneficiarioEhIgualTitularConta) {

                    cpfCnpj = $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val();
                    nome = $("#solicitacaoTransiente_beneficiario_pessoa_nome").val();
                }

                if (cpfCnpj !== "" && nome !== "") {
                    preecherCamposCpfCnpjNomeFinalidadePIX(cpfCnpj, nome);
                }
            } else {
                //console.log("Null" );
            }

        }
        
        function preencherCpfNomeQuandoTerceiros(name, cpfCnpj){
            var finalidade = document.getElementById('cb_tipoFinalidade').value;
            var beneficiarioEhIgualTitularConta = $("#rb_beneficiarioTitularContaTrue").is(':checked');
            if (finalidade === "CREDITO_CONTA_OUTRO_BANCO" && beneficiarioEhIgualTitularConta) {
                $("#finalidadeCreditoOutrosBancos_titular_nome").val(name);
                $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").val(cpfCnpj);
            }
        }
        
        function recuperarCpfCnpjBeneficiarioSelecionadoComMascara() {
            var cpfCnpj = "";
            if ($("#comboBeneficiario").val() !== "0") {
                cpfCnpj = $("#comboBeneficiario").find(':selected').attr('cpf');//01234567890 00000000000191
                cpfCnpj = mascaraCpfCnpj(cpfCnpj);
            }
            return cpfCnpj;
        }
        
        function preecherCamposCpfCnpjNomeFinalidade(cpfCnpj, nome) {
            $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").val(cpfCnpj);
            $("#finalidadeCreditoOutrosBancos_titular_nome").val(nome);
            $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").attr("readonly", "true");
            $("#finalidadeCreditoOutrosBancos_titular_nome").attr("readonly", "true");
        }
        
        //PIX
          function preecherCamposCpfCnpjNomeFinalidadePIX(cpfCnpj, nome) {
            console.log("cpf: "+$("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val());
            console.log("nome: "+$("#solicitacaoTransiente_beneficiario_pessoa_nome").val());
            $("#finalidadePIX_titular_cpfCnpj").val(cpfCnpj);
            $("#finalidadePIX_titular_nome").val(nome);
            $("#finalidadePIX_titular_nome").attr("readonly", "true");
            
            
          
            
            
        }
        
        function mascaraCpfCnpj (cpfCnpj) {
            if (cpfCnpj !== null && cpfCnpj !== undefined) {
                if (cpfCnpj.length == 11) {
                    var g1 = cpfCnpj.substring(0, 3);
                    var g2 = cpfCnpj.substring(3, 6);
                    var g3 = cpfCnpj.substring(6, 9);
                    var g4 = cpfCnpj.substring(9, 11);
                    return g1 + "." + g2 + "." + g3 + "-" + g4;
                }
                if (cpfCnpj.length == 14) {
                    var g1 = cpfCnpj.substring(0, 2);
                    var g2 = cpfCnpj.substring(2, 5);
                    var g3 = cpfCnpj.substring(5, 8);
                    var g4 = cpfCnpj.substring(8, 12);
                    var g5 = cpfCnpj.substring(12, 14);
                    return g1 + "." + g2 + "." + g3 + "/" + g4 + "-" + g5;
                }
            }
            return cpfCnpj;
        }
        
        function limparBeneficiario() {
        	var spanAvisoCPF = $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj");
        	if (spanAvisoCPF!=undefined) spanAvisoCPF.fadeOut();
            //esconderOuApresentarLinhaBeneficiarioCpfCnpj();
            limparCpfCnpjNomeSolicitacao();
            limparCpfCnpjNomeFinalidade();
            limpaElementosHiddenBeneficiario();
        }
        
        function verificarBeneficiarioSelecionado() {
           // debugger;
            if ($("#comboBeneficiario").val() !== "0") {
                $("#beneficiario").val($("#beneficiarioTransiente").val());
                preencherCampoCpfCnpj(); 
                carregarCpfCnpjNomeBeneficiarioTitularConta();
            } else {
                limparCpfCnpjNomeSolicitacao();
                limparCpfCnpjNomeFinalidade();
                limparCampoCpfCnpj();
            }
            montaComboTitularContaPIX();
        }
        

        function limparCampoCpfCnpj() {
            $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val("");
            $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").prop("disabled", false);
        }
        
        function esconderOuApresentarLinhaBeneficiarioCpfCnpj() {               
            if (isTipoBeneficiarioSelecionadoSomenteSelecao()) {
                $("#linha_beneficiario_cpfCnpj").fadeOut();
                $("#linha_beneficiario_nome").fadeOut();
                $('#lb_msg_cpf_cnpj_quantidade_digitos').css('display', 'none');
            } else {
                $("#linha_beneficiario_cpfCnpj").fadeIn();
                $("#linha_beneficiario_nome").fadeIn();
                $('#lb_msg_cpf_cnpj_quantidade_digitos').css('display', 'block');
            }
        }
               
        function isTipoBeneficiarioSelecionadoSomenteSelecao() {
              //  var tiposBeneficiariosSomenteSelecao = ['1', '5'];
            var tiposBeneficiariosSomenteSelecao = ['1', '5', '9', '10'];
            var tipoBeneficiarioSelecionado = $("#cb_tipoBeneficiario").val();
            return tiposBeneficiariosSomenteSelecao.includes(tipoBeneficiarioSelecionado);
        }
        
        function preencherCampoCpfCnpj() {
            var cpfCnpj = mascaraCpfCnpj($("#comboBeneficiario").val());
            $("#linha_beneficiario_cpfCnpj").fadeIn();
            
			// Pra qualquer das situaï¿½ï¿½es, o CPF/CNPJ deve ser desabilitado. 
          //  $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").prop("disabled", true);
			
            if (cpfCnpj) {
                $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val(cpfCnpj);
                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").fadeOut();
                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").text("");
            } else {
                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").fadeIn();
                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").text("CPF/CNPJ não informado. Retifique o cadastro da parte no processo");
            }
        }
        
        function limparCpfCnpjNomeSolicitacao() {
                $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val("");
                $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeAttr("readonly");
                $("#solicitacaoTransiente_beneficiario_pessoa_nome").val("");
                $("#solicitacaoTransiente_beneficiario_pessoa_nome").attr("readonly", "false");
        }
        
        function limparCpfCnpjNomeFinalidade() {
                $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").val("");
                $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").removeAttr("readonly");
                $("#finalidadeCreditoOutrosBancos_titular_nome").val("");
                $("#finalidadeCreditoOutrosBancos_titular_nome").attr("readonly", "true");
        }
        
        function limparCpfCnpjNomeFinalidadePIX() {
                $("#finalidadePIX_titular_cpfCnpj").val("");
                $("#finalidadePIX_titular_cpfCnpj").removeAttr("readonly");
                $("#finalidadePIX_titular_nome").val("");
                $("#finalidadePIX_titular_nome").attr("readonly", "true");
        }
        
        
        function byPassCpfCnpjBeneficiarioConta() {
            $("#solicitacaoTransiente_beneficiario_pessoa_nome").trigger("onblur");
            montaComboTitularContaPIX();
        }

        function cbTipoBeneficiarioChange(){
            limparBeneficiario();
            addChange();
        }
        
        function addChange() {
            var eventos = "validaCpfCnpj_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj();";//$("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").attr("onblur");
            eventos += "byPassCpfCnpjBeneficiarioConta();";
            $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").attr("onblur", eventos);
            $("#solicitacaoTransiente_procurador_cpfCnpj").attr("onblur", "montaComboTitularContaPIX()");
            $("#solicitacaoTransiente_representanteLegal_cpfCnpj").attr("onblur", "montaComboTitularContaPIX()");
        }
        
        function montaComboTitularContaPIX(){
            var cpf_beneficiario = $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val();
            var nm_beneficiario  = "";
            var beneficiario_selecionado = $('#comboBeneficiario').find(":selected").val();

            if(beneficiario_selecionado !== '0' && beneficiario_selecionado !== undefined){
                nm_beneficiario = $('#comboBeneficiario').find(":selected").text();
            }else{
                if(cpf_beneficiario !== undefined && cpf_beneficiario !== null && cpf_beneficiario.length > 0){
                    nm_beneficiario = recuperaNomePorCpfCnpj(cpf_beneficiario); 
                }
            }

            var select = document.querySelector('#select_titular');            
            if(select !== null){
                var cont = select.length;
                   while(select.length > 0){
                       console.log(select.length);
                          select.remove(cont--);
                   }
                select.options[select.options.length] = new Option("SELECIONE...",  "");

                //#Beneficiario    
                if(cpf_beneficiario !== undefined && cpf_beneficiario !== null && cpf_beneficiario.length > 0){
                    select.options[select.options.length] = new Option(cpf_beneficiario+" -"+ nm_beneficiario, cpf_beneficiario+" - "+ nm_beneficiario);
                 }
             }

            //#Procurador
            var cpf_procurador = $("#solicitacaoTransiente_procurador_cpfCnpj").val();
            var nm_procurador  =""; 

            if(cpf_procurador !== undefined && cpf_procurador !== null && cpf_procurador.length > 13){
                nm_procurador = recuperaNomePorCpfCnpj(cpf_procurador); 
                $("#solicitacaoTransiente\\.procurador\\.nome").val(nm_procurador);
                if(select !== null){
                    select.options[select.options.length] = new Option(cpf_procurador+" -"+ nm_procurador, cpf_procurador+" - "+ nm_procurador);
                }
             }

            //#Representante Legal
            var cpf_representante = $("#solicitacaoTransiente_representanteLegal_cpfCnpj").val();
            var nm_representante  =""; 

            if(cpf_representante !== undefined && cpf_representante !== null && cpf_representante.length > 13){
                nm_representante = recuperaNomePorCpfCnpj(cpf_representante); 
                $("#solicitacaoTransiente\\.representanteLegal\\.nome").val(nm_representante);
                if(select !== null){
                    select.options[select.options.length] = new Option(cpf_representante+" -"+ nm_representante, cpf_representante+" - "+ nm_representante);
                }
             }  
            preecherCamposTransicaoCpfCnpjNomeFinalidadePIX();  
          }
          
          function preecherCamposTransicaoCpfCnpjNomeFinalidadePIX() {
            var valorComboChavePix = $("#select_titular").val();
            if(valorComboChavePix !== undefined){
                var arrayAtributos =  valorComboChavePix.split(" - "); 

                console.log("nome: "+arrayAtributos[1]);
                $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").val(arrayAtributos[0]);
                $("#finalidadeCreditoOutrosBancos_titular_nome").val(arrayAtributos[1]);
            }
        }

        function recuperaNomePorCpfCnpj(cpfCnpj){
            var nomeUserCpf="";
            cpfCnpj = cpfCnpj.replaceAll(".", "").replaceAll("-","").replaceAll("/", "");
            //mostrarTelaCarregando();
            console.log("bloqueio de tela!");
            //const mostrarTelaCarregando = () => $("#bloqueio").addClass("escurecer");
           // const esconderTelaCarregando = () => $("#bloqueio").removeClass("escurecer");
            const retornoComSucesso = (data) => nomeUserCpf = data;

            $.ajax(
                "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validar.json",
                {
                  //  beforeSend: mostrarTelaCarregando,
                    success: retornoComSucesso,
                    dataType: "text",
                    async: false
                }
            )
           // .complete(esconderTelaCarregando);

            return nomeUserCpf;
        }
                
        function exibirLinhaCpfCnpjBeneficiario() {
            if (($("#cb_tipoFinalidade").val() === "CREDITO_CONTA_BB" || $("#cb_tipoFinalidade").val() === "CREDITO_CONTA_OUTRO_BANCO") 
            && $("#comboBeneficiario").val() !== "0") {
                var cpfCnpj = recuperarCpfCnpjBeneficiarioSelecionadoComMascara();
                $("#labelCpfCnpj").val(cpfCnpj);
                $("#linhaCpfCnpjBeneficiario").fadeIn();
            }
        }
        
        function ocultarLinhaCpfCnpjBeneficiario() {
            $("#labelCpfCnpj").val("");
            $("#linhaCpfCnpjBeneficiario").fadeOut();
        }
        
        function reloadTipoBeneficiario(){
             if($("#cb_tipoBeneficiario").val() !== "" ){
                    
                        var valor_tipo_beneficiario = $("#cb_tipoBeneficiario").val();
                        if(valor_tipo_beneficiario === "9" || valor_tipo_beneficiario === "10" || valor_tipo_beneficiario ==="11"){
                                $("#linha_beneficiario_cpfCnpj").fadeIn();
                                $("#linha_beneficiario_nome").fadeIn();
                        }
                        if(valor_tipo_beneficiario === "1" || valor_tipo_beneficiario === "5" || valor_tipo_beneficiario === "1" 
                        || valor_tipo_beneficiario === "3" || valor_tipo_beneficiario === "7" || valor_tipo_beneficiario === ""
                        || valor_tipo_beneficiario === null || valor_tipo_beneficiario === "0"){
                                
                                $("#linha_beneficiario_cpfCnpj").fadeOut();
                                $("#linha_beneficiario_nome").fadeOut();

                        }

                        var opt = $("#cb_tipoBeneficiario > option:checked");
                        var papel = opt.attr('papel');
                        abrirCombo(papel);
                        $("#linhaBeneficiario").css("opacity","1");
                     //   exibirDadosBeneficiario();
             }   
        }
        
        function carregarTipoBeneficiario(){
                $("#cb_tipoBeneficiario").val();
        }
        
        function criarChanges(){
                $("#rb_procurador").change(function(){ 
                        if($(this).is(':checked')){
                                exibirConteudoProcurador();
                        }else{
                                ocultarConteudoProcurador();
                                limparCamposProcurador();
                                $('#cb_estados').prop('selectedIndex',0); 
                                $('#cb_estados').trigger("chosen:updated");
                        }
                        verificarInclusaoCampoFolhaProcuracao();
                });
                
                $("#rb_representanteLegal").change(function(){
                        if($(this).is(':checked')){
                                exibirConteudoRepresentanteLegal();
                        }else{
                                ocultarConteudoRepresentanteLegal();
                                limparCamposRepresentanteLegal();
                        }
                        verificarInclusaoCampoFolhaProcuracao();
                });
                
                function changeTipoBeneficiario(){
                       limpaElementosHiddenBeneficiario()
                        var opt = $("#cb_tipoBeneficiario > option:checked");
                        var tipo = opt.attr('tipo');
                        var papel = opt.attr('papel');
                        
                        switch(tipo){
                                case "AUTOR":
                                        abrirCombo(papel);
                                       // exibirDadosBeneficiario();
                                        break;
                                
                                case "REU":
                                        abrirCombo(papel);
                                      //  exibirDadosBeneficiario();
                                        break;
                                
                                case "ADVOGADO":
                                        abrirCombo(papel);
                                      //  exibirDadosBeneficiario();
                                        break;
                                
                                case "OUTROS":
                                      comLinhaCpfNomeBeneficiario();
                                      
                                      //  exibirDadosBeneficiario();
                                        break;
                                     
                                default: 
//                                        $("#linhaBeneficiario").fadeOut();
                                        //abrirCombo(papel);
                                        //exibirDadosBeneficiario();
                                        resetBeneficiario();
                                        break;
                        }                
                }
                $("#cb_tipoBeneficiario").change(changeTipoBeneficiario);
                $("#comboBeneficiario").change(function(){
                       $("#idBeneficiario").val($("#comboBeneficiario").val());
                       ocultarConteudoBeneficiario();
//                       if($("#comboBeneficiario").val()!=="0"){
//                                ocultarConteudoBeneficiario();
//                       }else{
//                                exibirConteudoBeneficiario();
//                       }
                });
        }
        
        function limparCamposProcurador(){
                $("#solicitacaoTransiente_procurador_cpfCnpj").val("");
                $("#solicitacaoTransiente\\.procurador\\.nome").val("");
                $("#solicitacaoTransiente\\.numeroRegistroOab").val("");
                $("#solicitacaoTransiente\\.tipoRegistroOab").val("");
        }
        
        function limparCamposRepresentanteLegal(){
                $("#solicitacaoTransiente_representanteLegal_cpfCnpj").val("");
                $("#solicitacaoTransiente\\.representanteLegal\\.nome").val("");
        }
        
        function limparCampoFolhaProcuracao(){
                $('#solicitacaoTransiente\\.folhaProcuracao').val('');
        }
    
        function exibirConteudoProcurador(){
                $("#linha_procurador_cpfCnpj").fadeIn();
                $("#linha_procurador_cpfCnpj").css('opacity', '1');
                $("#linha_procurador_nome").fadeIn();
                $("#linha_procurador_nome").css('opacity', '1');
                $("#linha_procurador_registroOAB").fadeIn();
                $("#linha_procurador_registroOAB").css('opacity', '1');
                $("#linha_procurador_ufOAB").fadeIn();
                $("#linha_procurador_ufOAB").css('opacity', '1');
                $("#linha_procurador_tipoOAB").fadeIn();
                $("#linha_procurador_tipoOAB").css('opacity', '1');
                
                $("#cb_estados").chosen();
                $("#cb_estados_chosen").css("width","150");
        }
        
        function exibirConteudoRepresentanteLegal(){
                $("#linha_representanteLegal_cpfCnpj").fadeIn();
                $("#linha_representanteLegal_cpfCnpj").css('opacity', '1');
                $("#linha_representanteLegal_nome").fadeIn();
                $("#linha_representanteLegal_nome").css('opacity', '1');
        }
        
        function exibirDadosBeneficiario(){
            $("#qtdeBeneficiarios").val($('#comboBeneficiario option').size());
            
           // exibirConteudoBeneficiario();
          
                if($("#qtdeBeneficiarios").val() !== null 
                && $("#qtdeBeneficiarios").val() <= 1
                ){
                 $("#linhaBeneficiario").fadeOut();
                }else{
                   $("#linhaBeneficiario").fadeIn();
                   if($("#comboBeneficiario").val()!== null && $("#comboBeneficiario").val()!=="0"){
                           ocultarConteudoBeneficiario();
                   }
                }
                
        }
        
        function exibirConteudoBeneficiario(){
                
                $("#linha_beneficiario_cpfCnpj").fadeIn();
                $("#linha_beneficiario_nome").fadeIn();

        }    
        
        function ocultarConteudoBeneficiario(){
                $("#linha_beneficiario_cpfCnpj").fadeOut();
                $("#linha_beneficiario_nome").fadeOut();
                
                if ($("#cb_tipoBeneficiario").val() === null || $("#cb_tipoBeneficiario").val() === "0") {
                        
                        $('#solicitacaoTransiente_beneficiario_pessoa_nome').val('');
                        $('#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj').val('');
                }
        }
        
        function ocultarConteudoProcurador(){
                $("#linha_procurador_cpfCnpj").fadeOut();
                $("#linha_procurador_nome").fadeOut();
                $("#linha_procurador_registroOAB").fadeOut();
                $("#linha_procurador_ufOAB").fadeOut();
                $("#linha_procurador_tipoOAB").fadeOut();
        }
        
        function ocultarConteudoRepresentanteLegal(){ 
                $("#linha_representanteLegal_cpfCnpj").fadeOut();
                $("#linha_representanteLegal_nome").fadeOut();
        }
        
        function verificarInclusaoCampoFolhaProcuracao(){
                if(!$("#rb_procurador").is(":checked") && !$("#rb_representanteLegal").is(":checked")){
                      $("#linhaFolhaProcuracao").fadeOut();
                      limparCampoFolhaProcuracao();
                }else{
                      $("#linhaFolhaProcuracao").fadeIn();    
                }
                montaComboTitularContaPIX();
        }
        
        function reloadRadioRepresentacao(){
            if($("#rb_procurador").is(":checked")){
                    $("#rb_procurador").trigger("change");
            }
            if($("#rb_representanteLegal").is(":checked")){
                    $("#rb_representanteLegal").trigger("change");
            }
        }
        
        function abrirCombo( papel ){
                $("#linhaBeneficiario").fadeIn();
                carregarComboParte(papel);
        }
        
        function carregarComboParte(papel){ 
                $("#comboBeneficiario").html("<option value='0' selected='selected'>Selecione...</option>");
                $("#comboBeneficiario").trigger("change");  
                var url = "/portaltrtsp/pages/consulta-processual-tribunal-session/"+papel;
                if(url.length > 0){
                        $.ajax({
                                dataType: "json",
                                url: url,
                                async: false,
                                success: function(data){
                                    $("#comboBeneficiario_chosen").hide();
                                        if(data !== 'undefined' && data.length > 0) {
                                                var optionHtml = "";
                                                $.each(data,function(i,element){
                                                    var dadosBeneficiario ="";
                                                        optionHtml += "<option value='"+element.cpfCnpj+"' cpf='"+element.cpfCnpj+"' >"+ element.nome +" </option>";
                                                        dadosBeneficiario ="<input type='hidden' id='"+element.cpfCnpj+"' value='"+element.cpfCnpj+";"+element.nome+";"+element.principal+";"+papel+"'>";
                                                        document.getElementById("camposBeneficiario").innerHTML +=dadosBeneficiario;
   
                                                });
                                                $("#comboBeneficiario").append(optionHtml);
                                                if(data[0].cpfCnpj.length > 0){
                                                    comLinhaComboBeneficiario();
                                                 }else{
                                                    comLinhaCpfNomeBeneficiario();
                                                }  
                                        }else{
                                                limpaElementosHiddenBeneficiario();
                                               // $("#beneficiarioTransiente").val(null); 
                                                comLinhaCpfNomeBeneficiario();
                                             }
                                        if($("#idBeneficiario").val() !== null && $("#idBeneficiario").val()!=="0"){       
                                                $("#comboBeneficiario").val($("#idBeneficiario").val());
                                        }
                                         $("#comboBeneficiario").chosen();
                                        $("#comboBeneficiario").trigger("chosen:updated");
                                        $("#comboBeneficiario_chosen").css("width","450");      
                                }
                        });
                } 
                
        }     

        function setarHiddens(id){
            if (id !== '0' && id !== 'undefined') {
                let valorAgrupado = $("#"+id).val();
                let valordesagrupado = valorAgrupado.split(";");
                preencheElementosHiddenBeneficiario(valordesagrupado[0], //cpfcnpj
                                                    valordesagrupado[1], //nome
                                                    valordesagrupado[2],// principal
                                                    valordesagrupado[3] //papel
                                                    //valordesagrupado[$("#idProcesso").val()] //numeroProcesso
                                                 );
             } 
             
           //document.getElementById("camposBeneficiario").innerHTML = "";
             
        }
        
        function preencheElementosHiddenBeneficiario(cpfCnpj,nome,partePrincipal,papel){

            $("#beneficiario_pessoa_nome").val(nome);
            $("#beneficiario_pessoa_cpfCnpj").val(cpfCnpj);
            $("#beneficiario_parte_principal").val(partePrincipal);
            $("#beneficiario_papel").val(papel);
            $("#beneficiario_processo").val($("#idProcesso").val());
            
               carregarParteSiscondj(cpfCnpj,partePrincipal,papel,$("#idProcesso").val());
              
        }
        
        function limpaElementosHiddenBeneficiario(){

            $("#comboBeneficiario").val('0');
            $("#beneficiario_pessoa_nome").val('');
            $("#beneficiario_pessoa_cpfCnpj").val('');
            $("#beneficiario_parte_principal").val('');
            $("#beneficiario_papel").val('');
            $("#beneficiario_processo").val('');
            $("#beneficiario_id").val('0'); 
            
           // document.getElementById("camposBeneficiario").innerHTML = "";
        }
        
          function carregarParteSiscondj(cpfCnpj,partePrincipal,papel,processo){ 
                var url = "/portaltrtsp/pages/verifica-parte-processo/"+cpfCnpj+"/"+partePrincipal+"/"+papel+"/"+processo;                       
                if(url.length > 0){
                        $.ajax({
                            dataType: "json",
                            url: url,
                            async: false,
                            success: function(data){
                                if(data !== 'undefined') {
                                        $("#beneficiario_id").val(data);
                                }else{
                                        $("#beneficiario_id").val('0'); 
                                    }  
                                }
                        });
                    }   
                }     

        
        
         function comLinhaComboBeneficiario(){
              
            $("#linhaBeneficiario").fadeIn();
            $("#comboBeneficiario_chosen").show();
            ocultarConteudoBeneficiario();
        }
        
        function comLinhaCpfNomeBeneficiario(){
            $("#linhaBeneficiario").fadeOut();
            exibirConteudoBeneficiario(); 
        }
        
        function resetBeneficiario(){
                removerDuplicados();
                $("#linhaBeneficiario").fadeOut();
                 ocultarConteudoBeneficiario();
                 $("#cb_tipoBeneficiario").val("").trigger("chosen:updated"); 
                 //removerDuplicados();
            }
            
            function removerDuplicados() {
                let elementos = document.querySelectorAll("#comboBeneficiario_chosen"); // Seleciona todos os itens duplicados
                if(elementos.length > 0)
                    for (let i = 1; i < elementos.length; i++) { // Mantï¿½m o primeiro, remove os outros
                        elementos[i].remove();
                    }
            }
        
        
          //PIX
    function verificaStatus(valor){
           console.log("verificaStatus(param)");
           var tp_finalidade = document.getElementById('cb_tipoFinalidade').value;
        if(tp_finalidade == "PIX"){
            if(valor==='N'){
                document.getElementById("text_cpfcnpjtitularconta").style.display= '';
                document.getElementById("combo_cpfcnpjtitularconta").style.display= 'none';
                document.getElementById("finalidadePIX_titular_cpfCnpj").value= '';
                 document.getElementById("finalidadePIX_titular_nome").value= '';
            }else{
                document.getElementById("titularesConta").selected="selected";
                document.getElementById("finalidadePIX_titular_nome").value= '';
                document.getElementById("combo_cpfcnpjtitularconta").style.display= '';
                document.getElementById("text_cpfcnpjtitularconta").style.display= 'none';
            }
        }else{
            console.log("No pix");
        }
    }

</script>


<tr class="finalidade_darf">
        <td class="titulo">Telefone</td>
        <td>
                <input id="finalidadeDARF.telefoneDDD" name="finalidadeDARF.telefoneDDD" type="text" value="" size="2" maxlength="2">
                -
                <input id="finalidadeDARF.telefoneNumero" name="finalidadeDARF.telefoneNumero" onkeypress="Mascara(this,Integer);" onkeyup="Mascara(this,Integer);" onkeydown="Mascara(this,Integer);" type="text" value="" size="9" maxlength="9">
        </td>
</tr>

<tr class="finalidade_darf">
        <td class="titulo">
                Código da Receita*
        </td>
        <td>
                

























 
 
 

 


<script type="text/javascript">

	var tagSelectedParentInternalId_cmb_finalidadeReceita = '';
	
	
	function getParentSelected_cmb_finalidadeReceita() {
		if(tagSelectedParentInternalId_cmb_finalidadeReceita.length) {
			return tagSelectedParentInternalId_cmb_finalidadeReceita;
		}

		var selectedValue = -1;
		var tagResourceRegex = "finalidadeReceita".replace("/","\\/");

		var url = new String(window.location);
		var regex = new RegExp("/"+tagResourceRegex+"\/(\d+)/");
		if (regex.test(url)) {
			selectedValue = url.match(regex)[1];
		}
		return selectedValue;
	}
    
	function getParentUri_cmb_finalidadeReceita() {
		return "finalidadeReceita/" + getParentSelected_cmb_finalidadeReceita();
	}

	function setSelectedParentInternalId_cmb_finalidadeReceita(id){
		tagSelectedParentInternalId_cmb_finalidadeReceita = id;
	}
</script>

<select id="cmb_finalidadeReceita" name="finalidadeDARF.codigo.id" class="dados_formulario" style="min-width: 250px; display: none;">
	
<option value="">Selecione...</option><option value="10">2030 - Entidades financeiras - balanço trimestral</option><option value="12">5869 - CPMF - Operaçoes de lançamento a débito em conta</option><option value="13">9438 - 1 - CIDE - Combustíveis - importação</option><option value="14">9100 - Parcelamento vinculado à receita bruta</option><option value="15">1150 - IOF - Operações de crédito - pessoa jurídica - o tomador de crédito é pessoa jurídica, incluindo as operações de mútup revistas no art. 13n da Lei n. 9.779/99</option><option value="1700">5936 - IRRF - Rendimento Decorrente de Decisão da JT, exceto o disposto no art 12-A, da Lei nº 7.713/1988</option><option value="1701">1889 - IRRF - Rendimentos Acumulados - art. 12-A da Lei nº 7.713/1988</option><option value="1900">3623 - Receita Dívida Ativa - Multa CLT</option><option value="2100">2877 - Multas previstas na legislação do seguro desemprego e abono salarial</option><option value="2300">2864 - Honorários Adv Sucumbência - PGFN</option><option value="2800">5835 - CONDENAÇÃO JUDICIAL</option><option value="3000">289 - MULTA DA CLT</option><option value="3400">3981 - Produto Depósitos Abandonados</option><option value="3300">7309 - DEPÓSITOS (MULTAS CLT) (EXTINTO)</option><option value="3700">5891 - Depósito Judicial - Projeto Garimpo</option><option value="3701">5918 - Depósito Judicial - Projeto Garimpo - Período Pandemia</option><option value="3900">6092 - Contribuições Previdenciárias - Recolhimento Exclusivo pela Justiça do Trabalho</option></select><div class="chosen-container chosen-container-single" style="width: 898px;" title="" id="cmb_finalidadeReceita_chosen"><a class="chosen-single" tabindex="-1"><span>6092 - Contribuições Previdenciárias - Recolhimento Exclusivo pela Justiça do Trabalho</span><div><b></b></div></a><div class="chosen-drop"><div class="chosen-search"><input type="text" autocomplete="off"></div><ul class="chosen-results"><li class="active-result result-selected" style="" data-option-array-index="0">Selecione...</li><li class="active-result" style="" data-option-array-index="1">2030 - Entidades financeiras - balanço trimestral</li><li class="active-result" style="" data-option-array-index="2">5869 - CPMF - Operaçoes de lançamento a débito em conta</li><li class="active-result" style="" data-option-array-index="3">9438 - 1 - CIDE - Combustíveis - importação</li><li class="active-result" style="" data-option-array-index="4">9100 - Parcelamento vinculado à receita bruta</li><li class="active-result" style="" data-option-array-index="5">1150 - IOF - Operações de crédito - pessoa jurídica - o tomador de crédito é pessoa jurídica, incluindo as operações de mútup revistas no art. 13n da Lei n. 9.779/99</li><li class="active-result" style="" data-option-array-index="6">5936 - IRRF - Rendimento Decorrente de Decisão da JT, exceto o disposto no art 12-A, da Lei nº 7.713/1988</li><li class="active-result" style="" data-option-array-index="7">1889 - IRRF - Rendimentos Acumulados - art. 12-A da Lei nº 7.713/1988</li><li class="active-result" style="" data-option-array-index="8">3623 - Receita Dívida Ativa - Multa CLT</li><li class="active-result" style="" data-option-array-index="9">2877 - Multas previstas na legislação do seguro desemprego e abono salarial</li><li class="active-result" style="" data-option-array-index="10">2864 - Honorários Adv Sucumbência - PGFN</li><li class="active-result" style="" data-option-array-index="11">5835 - CONDENAÇÃO JUDICIAL</li><li class="active-result" style="" data-option-array-index="12">289 - MULTA DA CLT</li><li class="active-result" style="" data-option-array-index="13">3981 - Produto Depósitos Abandonados</li><li class="active-result" style="" data-option-array-index="14">7309 - DEPÓSITOS (MULTAS CLT) (EXTINTO)</li><li class="active-result" style="" data-option-array-index="15">5891 - Depósito Judicial - Projeto Garimpo</li><li class="active-result" style="" data-option-array-index="16">5918 - Depósito Judicial - Projeto Garimpo - Período Pandemia</li><li class="active-result result-selected" style="" data-option-array-index="17">6092 - Contribuições Previdenciárias - Recolhimento Exclusivo pela Justiça do Trabalho</li></ul></div></div>
<img id="tribunais_ajaxGif_cmb_finalidadeReceita" style="display: none;" src="/portaltrtsp/images/loading.gif">





<script type="text/javascript">
        
        function mostrarLoading_cmb_finalidadeReceita(){
                $("#tribunais_ajaxGif_cmb_finalidadeReceita").show();
        }
        
        function esconderLoading_cmb_finalidadeReceita(){
                $("#tribunais_ajaxGif_cmb_finalidadeReceita").hide();
        }

	function loadChosenParent_cmb_finalidadeReceita() {
		
			$("#cmb_finalidadeReceita").chosen({
				no_results_text: "Nenhum resultado",
				search_contains:true
			});
		    
		

		
		
		
	}

	function loadParent_cmb_finalidadeReceita(selectedId, parameters, postLoadFunction) {
		var url = "";

		var params = "";
		if(parameters && parameters.length) {
			params += parameters + "/";
		}

		

		url = "/portaltrtsp/pages/finalidadeReceita/" + params + "list.json";
		
		$.ajax({
			dataType: "json",
			url: url,
			removeBloqueio: true,
			success: function(data) {
				mostrarLoading_cmb_finalidadeReceita();

				
				$("#cmb_finalidadeReceita").fillSelect(data, selectedId ? selectedId : getParentSelected_cmb_finalidadeReceita());

				$("#cmb_finalidadeReceita").chosen("destroy");

				loadChosenParent_cmb_finalidadeReceita();

				if(postLoadFunction) {
					postLoadFunction();
				}

				esconderLoading_cmb_finalidadeReceita();

				
			}
		});
		
		
			
				
				$("#cmb_finalidadeReceita").change(function() {
					
				});
			
			
		
	}
	
	
	
	$(document).ready(function() {
		
			
				loadParent_cmb_finalidadeReceita();
			
			
		
	});
    
</script>
        </td>
</tr>

<tr class="finalidade_darf">
        <td class="titulo">Número de Referência*</td>
        <td>
                <input id="unidadeGestora" name="finalidadeDARF.numeroReferencia" onkeydown="Mascara(this,Integer);" onblur="Mascara(this,Integer);" type="text" value="" maxlength="17">
                
        </td>
</tr>

<tr class="finalidade_darf">
        <td class="titulo">Data de Apuração*</td>
        <td>
                <input id="periodoApuracao" name="finalidadeDARF.periodoApuracao" onkeydown="Mascara(this,Data);" type="text" value="" size="10" maxlength="10" class="hasDatepicker">
                

        </td>
</tr>

<tr class="finalidade_darf">
        <td class="titulo">Data de Vencimento*</td>
        <td>
                <input id="dataVencimento" name="finalidadeDARF.dataVencimento" onkeydown="Mascara(this,Data);" type="text" value="" size="10" maxlength="10" class="hasDatepicker">
                
        </td>
</tr>

<tr class="finalidade_darf">
        <td class="titulo">
                Valor do Principal (R$)*
        </td>
        <td>
                <input id="valorPrincipal" name="finalidadeDARF.valorPrincipal" class="mascara_valor" onblur="verificarValorPrincipal();" onchange="verificarValorPrincipal();" type="text" value="0,00" maxlength="16">
                
        </td>
</tr>

<tr class="finalidade_darf">
        <td class="titulo">
                Valor da Multa
        </td>
        <td>
                <input id="valorMulta" name="finalidadeDARF.valorMulta" class="mascara_valor" onblur="somarValorPrincipal();" onchange="somarValorPrincipal();" type="text" value="0,00" size="16" maxlength="16">
                
        </td>
</tr>

<tr class="finalidade_darf">
        <td class="titulo">
                Valor dos Juros
        </td>
        <td>
                <input id="valorJuros" name="finalidadeDARF.valorJuros" class="mascara_valor" onblur="somarValorPrincipal();" onchange="somarValorPrincipal();" type="text" value="0,00" size="16" maxlength="16">
                
        </td>
</tr>

<tr class="finalidade_darf">
        <td class="titulo">
                Valor (R$)*
        </td>
        <td>
                <input id="valor_real" name="solicitacaoTransiente.valorReal" class="mascara_valor" type="text" value="0,00" size="40" maxlength="20" readonly="readonly"> 
                (Do valor informado poderão ser descontados impostos e taxas.)
                
                
        </td>
</tr>
<tr class="finalidade_darf">
        <td class="titulo">
                Valor do Levantamento*
        </td>
        <td>
                <input id="rb_comCorrecao" name="solicitacaoTransiente.baseCalculo" class="correcao" type="radio" value="COM_ACRESCIMO"> 
                Com Correção 
                <input id="rb_semCorrecao" name="solicitacaoTransiente.baseCalculo" class="correcao" type="radio" value="SEM_ACRESCIMO"> 
                Sem Correção
                
        </td>
</tr>

<script>
        $(document).ready(function () {
                $("#periodoApuracao").datepicker();
                $("#dataVencimento").datepicker();

                $(".mascara_valor").maskMoney({
                        thousands: '.',
                        decimal: ',',
                        allowZero: true
                });
                $("#valor_real").attr("readOnly", true);
        });

        function verificarValorPrincipal() {
                var valorPrincipal = $("#valorPrincipal").val();
                var valor = valorPrincipal.replace(/[^0-9]/g, "");
                if (valor > 0) {
                        somarValorPrincipal();
                }
        }

        function somarValorPrincipal() {
                var valorMulta = $("#valorMulta").val().replace(/\./g, "");//retira mascara para soma
                if(valorMulta!==''){
                        valorMulta = parseFloat(valorMulta.replace(/\,/g, "."));//utiliza '.' na conversao para float
                }else{
                        valorMulta=0;
                }
                
                var valorJuros = $("#valorJuros").val().replace(/\./g, "");
                if(valorJuros!==''){
                        valorJuros = parseFloat(valorJuros.replace(/\,/g, "."));
                }else{
                        valorJuros=0;
                }
                
                var valorPrincipal = $("#valorPrincipal").val().replace(/\./g, "");
                if(valorPrincipal!==''){
                        valorPrincipal = parseFloat(valorPrincipal.replace(/\,/g, "."));
                }else{
                        valorPrincipal=0;
                }
                var total = 0;
                total = valorMulta+valorJuros+valorPrincipal;
                $("#valor_real").val(Valor(total.toFixed(2)));//converte e arredonda o resultado
                
                if(valorMulta>0 || valorJuros>0){
                        $('input:radio[name=solicitacaoTransiente\\.baseCalculo]:nth(1)').prop('checked',true);//sem correcao
                        $('#rb_comCorrecao').prop('disabled', true);
                }else{
                        $('input:radio[name=solicitacaoTransiente\\.baseCalculo]').prop('checked',false);//sem correcao
                        $('#rb_comCorrecao').prop('disabled', false);
                }
        }
</script>
                                        
                                        
                                        
                                        
                                        
                                         
                                        
                                
                        
                
                        
                
                                
                        </tbody>
                        
                                <tfoot>
                                        <tr>
                                                <td class="act_td" colspan="2">
                                                        <span class="bt_acessibilidade" title="Adicionar">
                                                                
                                                                        





















<input type="button" id="bt_add_solicitacao" class="botaoNovo" value="" onclick="executarAcao_bt_add_solicitacao()">

<script type="text/javascript">

	function executarAcao_bt_add_solicitacao(){
				
                
	            var retorno = true;

                
                        retorno = validarRequisicoesPendentes(false);
                
        
                
                        
                if(retorno) {
                        
                                
                                        $("#form_alvara").attr("action","/portaltrtsp/pages/mandado/pagamento/gerarSolicitacao");
                                        $("#form_alvara").submit();
                                 
                        
                }
	}
</script>

                                                                
                                                        </span>
                                                </td>
                                        </tr>
                                </tfoot>
                        
                </table>
        
   
       
            














        <br>
        <br>
        <table id="dados_solicitacao" class="relatorio">
                <caption>Solicitações do Alvará</caption>
                <tbody><tr>
                        <th width="14%">Número da Solicitação</th>
                        <th width="20%">Número da Conta</th>
                        <th width="12%">Parcela</th>
                        <th width="14%">Beneficiário</th>
                        <th width="14%">Valor Solicitação R$</th>
                        <th width="12%">Situação</th>
                        <th width="14%">Ações</th>
                </tr>
                </tbody><tbody>
                        
                            
                                
                                <tr>
                                        <td rowspan="2">1</td>
                                        <td style="padding: 0px;border:none;"></td>
                                        <td style="padding: 0px; border:none;"></td>
                                        <td rowspan="2">SELMA MARIA DOMINGOS</td>

                                        <td rowspan="2">
                                             9.164,04
                                        </td>
					
					<td rowspan="2">
                                                Gravado
					</td>
							
					<td rowspan="2">
						<a class="a-menu" style="margin: 2px;text-decoration: none; cursor: pointer;">
							<span id="4276491" class="bt-acao-visualizar" onclick="exibirSolicitacao(this);" alt="Visualizar" title="Visualizar"></span>
							<span id="processando_4276491"></span>
						</a>
                                                
							
								<a style="margin: 2px 5px; text-decoration: none; cursor: pointer;">
									<span id="cancelarSol_4276491" class="bt-acao-cancelar" onclick="abrirModalCancelarSolicitacao(4276491);" alt="Cancelar" title="Cancelar"></span>
									<span id="processando_4276491"></span>
								</a>
							
                                                
					</td>
                                </tr>
                                
                                        <tr>
                                                <td>600128877743</td>
                                                <td>2</td>
                                        </tr>
                                
                                        
                        

                </tbody>
        </table>
        <br>
        <br>
        <div id="detalhamentoAlvara" class="invisivel">                                                        
        </div>

        <div class="invisivel dialogo" id="div-cancelar-solicitacao" title="Confirmação de Cancelamento de Solicitação">
            A solicitação será cancelada e não será possível reverter. Deseja continuar? 
        </div>
              
       
        <script type="text/javascript">
                function abrirModalCancelarSolicitacao(idSolicitacao) {
                        var optionsDialog = {
                                width: '30%',
                                height: 'auto',
                                modal: true,
                                show: 'fade',
                                hide: 'fade',
                                background: 'white',
                                draggable: false,
                                top: 'auto',
                                position: {
                                        my: "center",
                                        at: "center",
                                        of: window,
                                        within: window
                                },
                                buttons: {
                                        "Sim": function () {
                                                $(this).dialog("close");
                                                cancelarSolicitacao(idSolicitacao);
                                        },
                                        "Não": function () {
                                                $(this).dialog("close");
                                        }
                                }
                        };
                        $("#div-cancelar-solicitacao").dialog(optionsDialog);
                }
        
                function cancelarSolicitacao(idSolicitacao){
                    $("#form_alvara").prop("action", "/portaltrtsp/pages/mandado/pagamento/solicitacao/cancelar/"+idSolicitacao);
                    $("#form_alvara").submit();
                }
                
        </script>
        















         
        
                <div id="detalhes_solicitacao" style="display: none">
                </div>

                <script type="text/javascript">
                        var optionsDialog = {
                                title: 'Visualizar Solicitação',
                                width: '700',
                                height: 'auto',
                                modal: true,
                                show: 'fade',
                                hide: 'fade',
                                draggable: false,
                                resizable: false

                        };

                        function exibirSolicitacao(componente) {
                             console.log(componente);
                                var idSolicitacao = $(componente).attr("id");

                                var detalhes_solicitacao = $("#detalhes_solicitacao");
                                detalhes_solicitacao.html("");

                                var url = "/portaltrtsp/pages/mandado/pagamento/solicitacao/exibir/" + idSolicitacao;

                                $.get(url, function (data) {
                                        detalhes_solicitacao.append(data);
                                });
                                $("#detalhes_solicitacao").dialog(optionsDialog);
                                var d = $(".ui-dialog").position();
                                window.scrollTo(d.left, d.top);
                        }
                </script>
        



            

        <div class="botoes centro">
                
                           
                         
                            















        



                

            

                

                

                

                

                
                
         
          

                           
                
            
            <input type="hidden" name="Grid" id="responsavelChamada" value="false">
            <!--Judicial
            
           grid: <input type="text" name="responsavelChamada" id="responsavelChamada" value="false">
            precat:<input type="text" name="alvaraForm.alvaraPrecatorio" id="alvaraPrecatorio" value="false">
            alvaraForm.getAlvaraPrecatorio(); -+   = 600128877743 ()
             -->
                

                 
             
                    
                        <span class="bt_acessibilidade" title="Voltar">
                                





















<input type="button" id="bt_voltar" class="botaoVoltar" value="" onclick="executarAcao_bt_voltar()">

<script type="text/javascript">

	function executarAcao_bt_voltar(){
				
                
	            var retorno = true;

                
                        retorno = voltarMovimentacao()
                
        
                
                        
                if(retorno) {
                        
                }
	}
</script>

                                <script type="text/javascript">
                                        function voltarMovimentacao() {
                                                id = $("#idProcesso").val();
                                                window.location = "/portaltrtsp/pages/movimentacao/conta/new/" + id;
                                        }
                                </script>
                              
                        </span>
                            
               
                
                        
                
            
            
        </div>
        <br>
        
</form>



ALVARÁ PERITO

<table id="tiposFinalidades" class="formulario">
                        <tbody id="tbodyFormAlvara">
                           
                                <tr id="trTipoFinalidade">                                  
                                        <td class="titulo">Tipo de Finalidade*</td>
                                        <td>
                                            <select id="cb_tipoFinalidade" name="tipoFinalidade" style="min-width: 100px; display: none;" onchange="abrirLinhasFinalidades();">
                                                        <option value="">Selecione...</option>
                                                        <option value="SAQUE_AGENCIA_BB">Comparecer ao Banco</option><option value="CREDITO_CONTA_BB">Crédito em Conta no Banco do Brasil</option><option value="CREDITO_CONTA_OUTRO_BANCO">Crédito em Conta para Outros Bancos</option><option value="PIX">Pix</option><option value="PAGAMENTO_GUIA">Pagamento de Guia</option><option value="TED_JUDICIAL">TED Judicial</option><option value="DARF">Pagamento de DARF</option><option value="GRU">Pagamento de GRU</option><option value="GPS">Pagamento de GPS</option><option value="NOVO_DEPOSITO">Novo Depósito Judicial</option>								
                                                </select><div class="chosen-container chosen-container-single" style="width: 280px;" title="" id="cb_tipoFinalidade_chosen"><a class="chosen-single" tabindex="-1"><span>Crédito em Conta no Banco do Brasil</span><div><b></b></div></a><div class="chosen-drop"><div class="chosen-search"><input type="text" autocomplete="off"></div><ul class="chosen-results"><li class="active-result result-selected" style="" data-option-array-index="0">Selecione...</li><li class="active-result" style="" data-option-array-index="1">Comparecer ao Banco</li><li class="active-result result-selected" style="" data-option-array-index="2">Crédito em Conta no Banco do Brasil</li><li class="active-result" style="" data-option-array-index="3">Crédito em Conta para Outros Bancos</li><li class="active-result" style="" data-option-array-index="4">Pix</li><li class="active-result" style="" data-option-array-index="5">Pagamento de Guia</li><li class="active-result" style="" data-option-array-index="6">TED Judicial</li><li class="active-result result-selected" style="" data-option-array-index="7">Pagamento de DARF</li><li class="active-result" style="" data-option-array-index="8">Pagamento de GRU</li><li class="active-result" style="" data-option-array-index="9">Pagamento de GPS</li><li class="active-result" style="" data-option-array-index="10">Novo Depósito Judicial</li></ul></div></div>
                                                <span id="cb_tipoFinalidade_errors" class="invisivel">Campo obrigatorio</span>
                                                
                                        </td>
                                </tr>
                        
                                
                                        
                                        
                                                


























<!-- Formulario de selecao de autor e reu

OBS: Passar o nome da classe via jsp:param.
-->

<tr id="linhaTipoBeneficiario" class="finalidade_credito_conta_bb">
        <td class="titulo">Tipo de Beneficiário*</td>
        <td>
            <input type="hidden" id="beneficiario_id" name="beneficiario.id" value="0">
            <input type="hidden" id="beneficiario_pessoa_nome" name="beneficiario.pessoa.nome" value="">
            <input type="hidden" id="beneficiario_pessoa_cpfCnpj" name="beneficiario.pessoa.cpfCnpj" value="">
            <input type="hidden" id="beneficiario_parte_principal" name="beneficiario.pessoa.principal" value="">
            <input type="hidden" id="beneficiario_papel" name="beneficiario.papel" value="">
            <input type="hidden" id="beneficiario_processo" name="beneficiario.processo.id" value="">
            
            <div id="camposBeneficiario">    <input type="hidden" id="96534300000120" value="96534300000120;HOSPITAL E MATERNIDADE VIDA" s="" ltda.;false;reclamado'=""><input type="hidden" id="67839969000121" value="67839969000121;AMEPLAN ASSISTENCIA MEDICA PLANEJADA LTDA.;false;RECLAMADO"><input type="hidden" id="07273957000150" value="07273957000150;CLINICA DE ESPECIALIDADE PARANAGUA LTDA;false;RECLAMADO"><input type="hidden" id="09338791000139" value="09338791000139;COMPLEXO HOSPITALAR J.S.J LTDA - EM RECUPERACAO JUDICIAL;false;RECLAMADO"><input type="hidden" id="06330689000107" value="06330689000107;PRONTO ATENDIMENTO SUPREMO LTDA;false;RECLAMADO"><input type="hidden" id="23642793000148" value="23642793000148;BETA SAUDE E PARTICIPACOES LTDA - EM RECUPERACAO JUDICIAL;false;RECLAMADO"><input type="hidden" id="96534300000120" value="96534300000120;HOSPITAL E MATERNIDADE VIDA" s="" ltda.;false;reclamado'=""><input type="hidden" id="67839969000121" value="67839969000121;AMEPLAN ASSISTENCIA MEDICA PLANEJADA LTDA.;false;RECLAMADO"><input type="hidden" id="07273957000150" value="07273957000150;CLINICA DE ESPECIALIDADE PARANAGUA LTDA;false;RECLAMADO"><input type="hidden" id="09338791000139" value="09338791000139;COMPLEXO HOSPITALAR J.S.J LTDA - EM RECUPERACAO JUDICIAL;false;RECLAMADO"><input type="hidden" id="06330689000107" value="06330689000107;PRONTO ATENDIMENTO SUPREMO LTDA;false;RECLAMADO"><input type="hidden" id="23642793000148" value="23642793000148;BETA SAUDE E PARTICIPACOES LTDA - EM RECUPERACAO JUDICIAL;false;RECLAMADO"></div>
            
        <select id="cb_tipoBeneficiario" name="tipoBeneficiario" style="min-width: 150px; display: none;" onchange="cbTipoBeneficiarioChange()">
			<option value="">Selecione...</option>
                        
                                <option value="10" papel="ADV_RECLAMADO" tipo="ADVOGADO">Adv Réu</option>
                        
                                <option value="9" papel="ADV_RECLAMANTE" tipo="ADVOGADO">Adv Autor</option>
                        
                                <option value="5" papel="RECLAMADO" tipo="REU">Réu</option>
                        
                                <option value="1" papel="RECLAMANTE" tipo="AUTOR">Autor</option>
                        
                                <option value="11" papel="TERCEIRO" tipo="OUTROS">Terceiro</option>
                        
		</select><div class="chosen-container chosen-container-single" style="width: 203px;" title="" id="cb_tipoBeneficiario_chosen"><a class="chosen-single" tabindex="-1"><span>Terceiro</span><div><b></b></div></a><div class="chosen-drop"><div class="chosen-search"><input type="text" autocomplete="off"></div><ul class="chosen-results"><li class="active-result" style="" data-option-array-index="0">Selecione...</li><li class="active-result" style="" data-option-array-index="1">Adv Réu</li><li class="active-result" style="" data-option-array-index="2">Adv Autor</li><li class="active-result result-selected" style="" data-option-array-index="3">Réu</li><li class="active-result" style="" data-option-array-index="4">Autor</li><li class="active-result result-selected" style="" data-option-array-index="5">Terceiro</li></ul></div></div>
                <input type="hidden" id="beneficiarioTransiente">
                <input type="hidden" id="beneficiario" name="beneficiario.id">
                <span id="cb_tipoBeneficiario_errors" class="invisivel">Campo obrigatorio</span>
                  
                <input type="hidden" id="qtdeBeneficiarios" name="qtdeBeneficiarios">
        </td>
</tr>
<tr id="linhaBeneficiario" style="display: none;" class="finalidade_credito_conta_bb">
        
        <td class="titulo">
                Beneficiário*
        </td>
        <td id="colunaBeneficiario">
        	<div id="divBeneficiario">
	            <select id="comboBeneficiario" onchange="verificarBeneficiarioSelecionado();setarHiddens(this.value)" style="display: none;"><option value="0" selected="selected">Selecione...</option><option value="96534300000120" cpf="96534300000120">HOSPITAL E MATERNIDADE VIDA'S LTDA. </option><option value="67839969000121" cpf="67839969000121">AMEPLAN ASSISTENCIA MEDICA PLANEJADA LTDA. </option><option value="07273957000150" cpf="07273957000150">CLINICA DE ESPECIALIDADE PARANAGUA LTDA </option><option value="09338791000139" cpf="09338791000139">COMPLEXO HOSPITALAR J.S.J LTDA - EM RECUPERACAO JUDICIAL </option><option value="06330689000107" cpf="06330689000107">PRONTO ATENDIMENTO SUPREMO LTDA </option><option value="23642793000148" cpf="23642793000148">BETA SAUDE E PARTICIPACOES LTDA - EM RECUPERACAO JUDICIAL </option></select><div class="chosen-container chosen-container-single" style="width: 450px; display: inline-block;" title="" id="comboBeneficiario_chosen"><a class="chosen-single chosen-default" tabindex="-1"><span>Selecione</span><div><b></b></div></a><div class="chosen-drop"><div class="chosen-search"><input type="text" autocomplete="off"></div><ul class="chosen-results"></ul></div></div>   
	            
            </div>
        </td>
</tr>
<tr id="linha_beneficiario_cpfCnpj" class="finalidade_credito_conta_bb" style="opacity: 1; display: table-row;">
        <td id="tituloBeneficiario_cpfCnpj" class="titulo">
                
                        
                              CPF/CNPJ do Beneficiário
                        
                        
                
                









<span title="Preencha o CPF ou CNPJ sem formatação." class="bt-acao-ajuda"> </span>
        </td>
        <td>
		

































        
        
<div style="float:left">
	<input id="solicitacaoTransiente_beneficiario_pessoa_cpfCnpj" name="solicitacaoTransiente.beneficiario.pessoa.cpfCnpj" onkeydown="Mascara(this,CpfCnpjContagem);" onblur="validaCpfCnpj_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj();byPassCpfCnpjBeneficiarioConta();" onchange="Mascara(this,CpfCnpjContagem);" type="text" value="96.534.300/0001-20" size="40" maxlength="18">
	





















<input type="button" id="solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button" class="botaoAtualizar invisivel" value="Validar" onclick="executarAcao_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button()">

<script type="text/javascript">

	function executarAcao_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button(){
				
                
	            var retorno = true;

                
                        retorno = validaCpfCnpj_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj();
                
        
                
                        
                if(retorno) {
                        
                }
	}
</script>

	<span id="span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj" class="invisible"></span>
	
        <br>
        <label id="lb_msg_cpf_cnpj_quantidade_digitos" style="color:#555555; font-size:10px;">(Informe 11 (onze) digitos para CPF ou 14 (quatorze) para CNPJ)</label>
</div>
<script type="text/javascript">
function validaCpfCnpj_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj() {
        $("#solicitacaoTransiente_beneficiario_pessoa_nome").val("");
	var cpfCnpj = Integer($("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val());
	cpfCnpj = cpfCnpj.replace(/[-./]/g, '');
	if(cpfCnpj == "") {
		
		    $("#solicitacaoTransiente_beneficiario_pessoa_nome").val("");
		    
		    
		    
		    $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('invisible');
		    $("#tribunais_ajaxGif_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button").hide();
		    $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button").removeAttr("disabled");
		
		return true;
	}

	if("CPFCNPJ" === 'CPFCNPJ'){

		if($("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val().length!=14 && $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val().length!=18){
		            aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	if("CPFCNPJ" === 'CPF'){

		if($("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val().length!=14){
		            aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	if("CPFCNPJ" === 'CNPJ'){

		if($("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val().length!=18){
		            aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	
	$("#tribunais_ajaxGif_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button").show();
		
	// realiza chamada WS
	$("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").trigger("eventIniciarRequisicaoAjax");
        
        
        //validar cpfcnpj nas partes do processo e no bb ou somento no bb
        if(true){
                var opt = $("#cb_tipoBeneficiario > option:checked");
                var tipo = opt.attr('tipo');
                var url = "/portaltrtsp/pages/processo/tribunal/"+$("#numeroProcesso").val()+"/cpfcnpj/"+cpfCnpj+"/"+tipo+"/validar.json";
        }else{      
                var url = "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validarModulo.json";
                
                        url = "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validar.json";
                
        }
        
        var ajaxReq = $.ajax(url, {
                dataType: "text",

                statusCode: {
                        200: function() { 
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldWithErrors');
                                aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("");
                                   
                        },
                        204: function() { 
                                aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("O CPF/CNPJ inválido ou formato incorreto."); 
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('fieldWithErrors');
                        },
                        404: function() { 
                                aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("Serviço WS para acessos externos não encontrado."); 
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('fieldWithErrors');
                        },
                        406: function() { 
                                aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("A consulta processual não retornou dados do CPF/CNPJ da parte informada."); 
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('fieldWithErrors');
                        },
                        500: function() { 
                                aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("Serviço externo indisponível. Tente novamente mais tarde."); 
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('fieldWithErrors');
                        },
                        503: function() { 
                                aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj("Serviço externo indisponível. Tente novamente mais tarde."); 
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('fieldWithErrors');
                        },
                        666: function(xhr) { 
                               console.log(xhr.responseText);
                              $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldSuccess');
                              $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('fieldWithErrors');
                              $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('invisible');	
                              $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('fieldWithErrors');
                              aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj(xhr.responseText);                        
                        }
                },

                
                        success: function(data, textStatus, jqXHR) {
                                $("#solicitacaoTransiente_beneficiario_pessoa_nome").val(data);
                                
                },
                

                complete: function() {
                    $("#tribunais_ajaxGif_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button").hide();
                    $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj_button").removeAttr("disabled");

                    
                        $("#solicitacaoTransiente_beneficiario_pessoa_nome\\.errors").hide();
                    

                    $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").trigger("eventFinalizarRequisicaoAjax");
                }
        });
	
	return true;
}

function aplicaResultado_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj(validacaoMsg) {
	if(validacaoMsg != ""){
		$("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeClass('invisible');	
	}else{
		$("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").addClass('invisible');
	}
    $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").html(validacaoMsg);
    
    
	    if(validacaoMsg == "") {
			$("#solicitacaoTransiente_beneficiario_pessoa_nome").attr("readonly", "readonly");
	    } else {
	    			
	    }
    
    
//    if(document.getElementById('cb_tipoFinalidade') != null){
//        var tp_finalidade = document.getElementById('cb_tipoFinalidade').value;
//        console.log("finalidade <:> " + tp_finalidade );
//        if(tp_finalidade === "PIX"){
//           //  this.montaComboTitularConta();
//            // window.addEventListener("load", function(){
//                    montaComboTitularConta(); 
//            //    });
//         }
//     }  
}



</script>
	</td>
</tr>

<tr id="linha_beneficiario_nome" class="finalidade_credito_conta_bb" style="opacity: 1; display: table-row;">
    <td id="tituloBeneficiario_nome" class="titulo">
            
                    
                          Nome Beneficiário
                    
                    
            
    </td>
    <td>
        <input id="solicitacaoTransiente_beneficiario_pessoa_nome" name="solicitacaoTransiente.beneficiario.pessoa.nome" readonly="readonly" type="text" value="" size="45" maxlength="100">
        
    </td>
</tr>


    
    
   
         
     
    <tr id="linhaBeneficiarioTitularConta">
        <td class="titulo">
            Beneficiário/Procurador/Representante é igual ao titular da conta?*
            









<span title="Sim: validar o CPF/CNPJ do beneficiário do resgate X Conta Destino.

Não: não será feito a validação podendo o recurso ser enviado para outra pessoa que não seja o Beneficiário." class="bt-acao-ajuda"> </span>
        </td>
        <td>
            <input id="rb_beneficiarioTitularContaTrue" name="finalidadeCreditoEmContaBB.indicadorBeneficiarioTitularConta" onload="beneficiarioEhTitularConta()" onchange=" carregarCpfCnpjNomeBeneficiarioTitularConta();verificarMostrarTitular();" type="radio" value="S"> 
            Sim
            <input id="rb_beneficiarioTitularContaFalse" name="finalidadeCreditoEmContaBB.indicadorBeneficiarioTitularConta" onclick="verificaStatus(this.value)" onchange="verificarMostrarTitular();" type="radio" value="N"> 
            Não
            
        </td>
    </tr>



    
    <tr id="selecao_tipoBeneficiario" class="finalidade_credito_conta_bb">
            <td class="titulo">Procurador / Representante Legal</td>
            <td>
                    <input id="rb_procurador" name="representantes" type="checkbox" value="PROCURADOR"><input type="hidden" name="_representantes" value="on">
                    Procurador
                    <input id="rb_representanteLegal" name="representantes" type="checkbox" value="REPRESENTANTE_LEGAL"><input type="hidden" name="_representantes" value="on">
                    Representante Legal

                    
            </td>
    </tr>

    <tr id="linha_procurador_cpfCnpj" class="finalidade_credito_conta_bb" style="display: none !important;">
                <td class="titulo">
                    CPF/CNPJ Procurador*
                    









<span title="Preencha o CPF ou CNPJ sem formatação." class="bt-acao-ajuda"> </span>
                </td>
                <td>
                        

































        
        
<div style="float:left">
	<input id="solicitacaoTransiente_procurador_cpfCnpj" name="solicitacaoTransiente.procurador.cpfCnpj" onkeydown="Mascara(this,CpfCnpjContagem);" onblur="montaComboTitularContaPIX()" onchange="Mascara(this,CpfCnpjContagem);" type="text" value="" size="40" maxlength="18">
	





















<input type="button" id="solicitacaoTransiente_procurador_cpfCnpj_button" class="botaoAtualizar invisivel" value="Validar" onclick="executarAcao_solicitacaoTransiente_procurador_cpfCnpj_button()">

<script type="text/javascript">

	function executarAcao_solicitacaoTransiente_procurador_cpfCnpj_button(){
				
                
	            var retorno = true;

                
                        retorno = validaCpfCnpj_solicitacaoTransiente_procurador_cpfCnpj();
                
        
                
                        
                if(retorno) {
                        
                }
	}
</script>

	<span id="span_solicitacaoTransiente_procurador_cpfCnpj" class="fieldWithErrors invisible"></span>
	
        <br>
        <label id="lb_msg_cpf_cnpj_quantidade_digitos" style="color:#555555; font-size:10px;">(Informe 11 (onze) digitos para CPF ou 14 (quatorze) para CNPJ)</label>
</div>
<script type="text/javascript">
function validaCpfCnpj_solicitacaoTransiente_procurador_cpfCnpj() {
        $("#solicitacaoTransiente\\.procurador\\.nome").val("");
	var cpfCnpj = Integer($("#solicitacaoTransiente_procurador_cpfCnpj").val());
	cpfCnpj = cpfCnpj.replace(/[-./]/g, '');
	if(cpfCnpj == "") {
		
		    $("#solicitacaoTransiente\\.procurador\\.nome").val("");
		    
		    
		    
		    $("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('invisible');
		    $("#tribunais_ajaxGif_solicitacaoTransiente_procurador_cpfCnpj_button").hide();
		    $("#solicitacaoTransiente_procurador_cpfCnpj_button").removeAttr("disabled");
		
		return true;
	}

	if("CPFCNPJ" === 'CPFCNPJ'){

		if($("#solicitacaoTransiente_procurador_cpfCnpj").val().length!=14 && $("#solicitacaoTransiente_procurador_cpfCnpj").val().length!=18){
		            aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	if("CPFCNPJ" === 'CPF'){

		if($("#solicitacaoTransiente_procurador_cpfCnpj").val().length!=14){
		            aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	if("CPFCNPJ" === 'CNPJ'){

		if($("#solicitacaoTransiente_procurador_cpfCnpj").val().length!=18){
		            aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	
	$("#tribunais_ajaxGif_solicitacaoTransiente_procurador_cpfCnpj_button").show();
		
	// realiza chamada WS
	$("#solicitacaoTransiente_procurador_cpfCnpj").trigger("eventIniciarRequisicaoAjax");
        
        
        //validar cpfcnpj nas partes do processo e no bb ou somento no bb
        if(false){
                var opt = $("#cb_tipoBeneficiario > option:checked");
                var tipo = opt.attr('tipo');
                var url = "/portaltrtsp/pages/processo/tribunal/"+$("#numeroProcesso").val()+"/cpfcnpj/"+cpfCnpj+"/"+tipo+"/validar.json";
        }else{      
                var url = "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validarModulo.json";
                
                        url = "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validar.json";
                
        }
        
        var ajaxReq = $.ajax(url, {
                dataType: "text",

                statusCode: {
                        200: function() { 
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldWithErrors');
                                aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("");
                                   
                        },
                        204: function() { 
                                aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("O CPF/CNPJ inválido ou formato incorreto."); 
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('fieldWithErrors');
                        },
                        404: function() { 
                                aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("Serviço WS para acessos externos não encontrado."); 
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('fieldWithErrors');
                        },
                        406: function() { 
                                aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("A consulta processual não retornou dados do CPF/CNPJ da parte informada."); 
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('fieldWithErrors');
                        },
                        500: function() { 
                                aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("Serviço externo indisponível. Tente novamente mais tarde."); 
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('fieldWithErrors');
                        },
                        503: function() { 
                                aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj("Serviço externo indisponível. Tente novamente mais tarde."); 
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('fieldWithErrors');
                        },
                        666: function(xhr) { 
                               console.log(xhr.responseText);
                              $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldSuccess');
                              $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('fieldWithErrors');
                              $("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('invisible');	
                              $("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('fieldWithErrors');
                              aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj(xhr.responseText);                        
                        }
                },

                
                        success: function(data, textStatus, jqXHR) {
                                $("#solicitacaoTransiente\\.procurador\\.nome").val(data);
                                
                },
                

                complete: function() {
                    $("#tribunais_ajaxGif_solicitacaoTransiente_procurador_cpfCnpj_button").hide();
                    $("#solicitacaoTransiente_procurador_cpfCnpj_button").removeAttr("disabled");

                    
                        $("#solicitacaoTransiente\\.procurador\\.nome\\.errors").hide();
                    

                    $("#solicitacaoTransiente_procurador_cpfCnpj").trigger("eventFinalizarRequisicaoAjax");
                }
        });
	
	return true;
}

function aplicaResultado_solicitacaoTransiente_procurador_cpfCnpj(validacaoMsg) {
	if(validacaoMsg != ""){
		$("#span_solicitacaoTransiente_procurador_cpfCnpj").removeClass('invisible');	
	}else{
		$("#span_solicitacaoTransiente_procurador_cpfCnpj").addClass('invisible');
	}
    $("#span_solicitacaoTransiente_procurador_cpfCnpj").html(validacaoMsg);
    
    
	    if(validacaoMsg == "") {
			$("#solicitacaoTransiente\\.procurador\\.nome").attr("readonly", "readonly");
	    } else {
	    			
	    }
    
    
//    if(document.getElementById('cb_tipoFinalidade') != null){
//        var tp_finalidade = document.getElementById('cb_tipoFinalidade').value;
//        console.log("finalidade <:> " + tp_finalidade );
//        if(tp_finalidade === "PIX"){
//           //  this.montaComboTitularConta();
//            // window.addEventListener("load", function(){
//                    montaComboTitularConta(); 
//            //    });
//         }
//     }  
}



</script>
                </td>
        </tr>
        <tr id="linha_procurador_nome" class="finalidade_credito_conta_bb" style="display: none !important;">
                <td class="titulo">Nome Procurador*</td>
                <td>
                        <input id="solicitacaoTransiente.procurador.nome" name="solicitacaoTransiente.procurador.nome" onchange="carregarListaPix()" type="text" value="" size="45" maxlength="100">
                        
                </td>
        </tr>
        <tr id="linha_procurador_registroOAB" class="finalidade_credito_conta_bb" style="display: none !important;">
                <td class="titulo">N° Registro OAB*</td>
                <td>
                        <input id="solicitacaoTransiente.numeroRegistroOab" name="solicitacaoTransiente.numeroRegistroOab" type="text" value="" size="10" maxlength="10">
                        
                </td>
        </tr>
        <tr id="linha_procurador_ufOAB" class="finalidade_credito_conta_bb" style="display: none !important;">
                <td class="titulo">
                        UF OAB*
                </td>   
                <td>
                        <select id="cb_estados" name="solicitacaoTransiente.estado" style="min-width:150px;">
                                <option value="" selected="selected">Selecione...</option>
                                <option value="AC">AC</option><option value="AL">AL</option><option value="AM">AM</option><option value="AP">AP</option><option value="BA">BA</option><option value="CE">CE</option><option value="DF">DF</option><option value="ES">ES</option><option value="GO">GO</option><option value="MA">MA</option><option value="MG">MG</option><option value="MS">MS</option><option value="MT">MT</option><option value="PA">PA</option><option value="PB">PB</option><option value="PE">PE</option><option value="PI">PI</option><option value="PR">PR</option><option value="RJ">RJ</option><option value="RN">RN</option><option value="RO">RO</option><option value="RR">RR</option><option value="RS">RS</option><option value="SC">SC</option><option value="SE">SE</option><option value="SP">SP</option><option value="TO">TO</option>
                        </select>
                        
                </td>
        </tr>
        <tr id="linha_procurador_tipoOAB" class="finalidade_credito_conta_bb" style="display: none !important;">
                <td class="titulo">
                        Tipo OAB*
                </td>
                <td>
                        <input id="solicitacaoTransiente.tipoRegistroOab" name="solicitacaoTransiente.tipoRegistroOab" type="text" value="" size="20" maxlength="20">
                        

                </td>
        </tr>

    <tr id="linha_representanteLegal_cpfCnpj" class="finalidade_credito_conta_bb" style="display: none !important;">
                <td class="titulo">
                    CPF/CNPJ Representante Legal*
                    









<span title="Preencha o CPF ou CNPJ sem formatação." class="bt-acao-ajuda"> </span>
                </td>
                <td>
                        

































        
        
<div style="float:left">
	<input id="solicitacaoTransiente_representanteLegal_cpfCnpj" name="solicitacaoTransiente.representanteLegal.cpfCnpj" onkeydown="Mascara(this,CpfCnpjContagem);" onblur="montaComboTitularContaPIX()" onchange="Mascara(this,CpfCnpjContagem);" type="text" value="" size="40" maxlength="18">
	





















<input type="button" id="solicitacaoTransiente_representanteLegal_cpfCnpj_button" class="botaoAtualizar invisivel" value="Validar" onclick="executarAcao_solicitacaoTransiente_representanteLegal_cpfCnpj_button()">

<script type="text/javascript">

	function executarAcao_solicitacaoTransiente_representanteLegal_cpfCnpj_button(){
				
                
	            var retorno = true;

                
                        retorno = validaCpfCnpj_solicitacaoTransiente_representanteLegal_cpfCnpj();
                
        
                
                        
                if(retorno) {
                        
                }
	}
</script>

	<span id="span_solicitacaoTransiente_representanteLegal_cpfCnpj" class="fieldWithErrors invisible"></span>
	
        <br>
        <label id="lb_msg_cpf_cnpj_quantidade_digitos" style="color:#555555; font-size:10px;">(Informe 11 (onze) digitos para CPF ou 14 (quatorze) para CNPJ)</label>
</div>
<script type="text/javascript">
function validaCpfCnpj_solicitacaoTransiente_representanteLegal_cpfCnpj() {
        $("#solicitacaoTransiente\\.representanteLegal\\.nome").val("");
	var cpfCnpj = Integer($("#solicitacaoTransiente_representanteLegal_cpfCnpj").val());
	cpfCnpj = cpfCnpj.replace(/[-./]/g, '');
	if(cpfCnpj == "") {
		
		    $("#solicitacaoTransiente\\.representanteLegal\\.nome").val("");
		    
		    
		    
		    $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('invisible');
		    $("#tribunais_ajaxGif_solicitacaoTransiente_representanteLegal_cpfCnpj_button").hide();
		    $("#solicitacaoTransiente_representanteLegal_cpfCnpj_button").removeAttr("disabled");
		
		return true;
	}

	if("CPFCNPJ" === 'CPFCNPJ'){

		if($("#solicitacaoTransiente_representanteLegal_cpfCnpj").val().length!=14 && $("#solicitacaoTransiente_representanteLegal_cpfCnpj").val().length!=18){
		            aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	if("CPFCNPJ" === 'CPF'){

		if($("#solicitacaoTransiente_representanteLegal_cpfCnpj").val().length!=14){
		            aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	if("CPFCNPJ" === 'CNPJ'){

		if($("#solicitacaoTransiente_representanteLegal_cpfCnpj").val().length!=18){
		            aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("Quantidade de dígitos inválidos. Preencha os 11 dígitos para o Cpf Ou os 14 dígitos para Cnpj.");
		            return;
	   	}
	}
	
	$("#tribunais_ajaxGif_solicitacaoTransiente_representanteLegal_cpfCnpj_button").show();
		
	// realiza chamada WS
	$("#solicitacaoTransiente_representanteLegal_cpfCnpj").trigger("eventIniciarRequisicaoAjax");
        
        
        //validar cpfcnpj nas partes do processo e no bb ou somento no bb
        if(false){
                var opt = $("#cb_tipoBeneficiario > option:checked");
                var tipo = opt.attr('tipo');
                var url = "/portaltrtsp/pages/processo/tribunal/"+$("#numeroProcesso").val()+"/cpfcnpj/"+cpfCnpj+"/"+tipo+"/validar.json";
        }else{      
                var url = "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validarModulo.json";
                
                        url = "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validar.json";
                
        }
        
        var ajaxReq = $.ajax(url, {
                dataType: "text",

                statusCode: {
                        200: function() { 
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldWithErrors');
                                aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("");
                                   
                        },
                        204: function() { 
                                aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("O CPF/CNPJ inválido ou formato incorreto."); 
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('fieldWithErrors');
                        },
                        404: function() { 
                                aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("Serviço WS para acessos externos não encontrado."); 
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('fieldWithErrors');
                        },
                        406: function() { 
                                aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("A consulta processual não retornou dados do CPF/CNPJ da parte informada."); 
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('fieldWithErrors');
                        },
                        500: function() { 
                                aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("Serviço externo indisponível. Tente novamente mais tarde."); 
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('fieldWithErrors');
                        },
                        503: function() { 
                                aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj("Serviço externo indisponível. Tente novamente mais tarde."); 
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldSuccess');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldWithErrors');
                                $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('fieldWithErrors');
                        },
                        666: function(xhr) { 
                               console.log(xhr.responseText);
                              $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldSuccess');
                              $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('fieldWithErrors');
                              $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('invisible');	
                              $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('fieldWithErrors');
                              aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj(xhr.responseText);                        
                        }
                },

                
                        success: function(data, textStatus, jqXHR) {
                                $("#solicitacaoTransiente\\.representanteLegal\\.nome").val(data);
                                
                },
                

                complete: function() {
                    $("#tribunais_ajaxGif_solicitacaoTransiente_representanteLegal_cpfCnpj_button").hide();
                    $("#solicitacaoTransiente_representanteLegal_cpfCnpj_button").removeAttr("disabled");

                    
                        $("#solicitacaoTransiente\\.representanteLegal\\.nome\\.errors").hide();
                    

                    $("#solicitacaoTransiente_representanteLegal_cpfCnpj").trigger("eventFinalizarRequisicaoAjax");
                }
        });
	
	return true;
}

function aplicaResultado_solicitacaoTransiente_representanteLegal_cpfCnpj(validacaoMsg) {
	if(validacaoMsg != ""){
		$("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").removeClass('invisible');	
	}else{
		$("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").addClass('invisible');
	}
    $("#span_solicitacaoTransiente_representanteLegal_cpfCnpj").html(validacaoMsg);
    
    
	    if(validacaoMsg == "") {
			$("#solicitacaoTransiente\\.representanteLegal\\.nome").attr("readonly", "readonly");
	    } else {
	    			
	    }
    
    
//    if(document.getElementById('cb_tipoFinalidade') != null){
//        var tp_finalidade = document.getElementById('cb_tipoFinalidade').value;
//        console.log("finalidade <:> " + tp_finalidade );
//        if(tp_finalidade === "PIX"){
//           //  this.montaComboTitularConta();
//            // window.addEventListener("load", function(){
//                    montaComboTitularConta(); 
//            //    });
//         }
//     }  
}



</script>
                </td>
        </tr>
        <tr id="linha_representanteLegal_nome" class="finalidade_credito_conta_bb" style="display: none !important;">
                <td class="titulo">Nome Representante Legal*</td>
                <td>
                        <input id="solicitacaoTransiente.representanteLegal.nome" name="solicitacaoTransiente.representanteLegal.nome" onchange="carregarListaPix()" type="text" value="" size="45" maxlength="100">
                        
                </td>
        </tr>

    <tr id="linhaFolhaProcuracao" class="finalidade_credito_conta_bb" style="opacity: 1; display: none;">
            <td class="titulo">
                    Folha da Procuração
            </td>
            <td>
                    <input id="solicitacaoTransiente.folhaProcuracao" name="solicitacaoTransiente.folhaProcuracao" type="text" value="">
                    
            </td>
    </tr>

    
<script type="text/javascript">
    
    function carregarListaPix(){
        var combo = document.getElementById('pixDi1namico');

        if (combo !== null && combo !== undefined){ 
            for (a in combo.options) { combo.options.remove(a); }
        }

        var podeSelecionar = document.getElementById('rb_beneficiarioTitularContaFalse').checked;

        if(!podeSelecionar){
            $("#linhaChavePixDinamico").fadeOut();
            $("#linhaChavePixCpfCnpjBeneficiario").fadeIn();
            
            var cpfCnpj = $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val();
            var nome = $("#solicitacaoTransiente_beneficiario_pessoa_nome").val();

            preecherCamposCpfCnpjNomeFinalidadePIX(cpfCnpj, nome);
            
            return;
                
        }
        
        $("#linhaChavePixDinamico").fadeIn();
        $("#linhaChavePixCpfCnpjBeneficiario").fadeOut();

        var beneficiario = document.getElementById('solicitacaoTransiente_beneficiario_pessoa_cpfCnpj').value;

        var procurador = document.getElementById('solicitacaoTransiente_procurador_cpfCnpj').value;

        var representante = document.getElementById('solicitacaoTransiente_representanteLegal_cpfCnpj').value;



        combo.appendChild(new Option('Selecione','selecione'));
        
        if(beneficiario !== null && beneficiario.trim().length !== 0){
            combo.appendChild(new Option(beneficiario,beneficiario));
        }

        if(procurador !== null && procurador.trim().length !== 0){
            combo.appendChild(new Option(procurador,procurador));
        }
        
        if(representante !== null && representante.trim().length !== 0){
            combo.appendChild(new Option(representante,representante));
        }
        
        
        combo.addEventListener('change', function handle(event){
            var selectElement = event.target;
            var value = selectElement.value;    
            
            
            var value2 = combo.options[combo.selectedIndex].value;
            var text2 = combo.options[combo.selectedIndex].text;
            
            preecherCamposCpfCnpjNomeFinalidadePIX(value2, text2);
            
        });
    }
    
        var finalidade = document.getElementById('cb_tipoFinalidade').value;
        
        if (finalidade === "CREDITO_CONTA_BB" || finalidade === "CREDITO_CONTA_OUTRO_BANCO" || finalidade === "PIX") {
            document.getElementById('rb_beneficiarioTitularContaFalse').addEventListener('click', function(e){  
                limparCpfCnpjNomeFinalidade();
            });

            document.getElementById('rb_beneficiarioTitularContaTrue').addEventListener('click', function(e){  
                carregarCpfCnpjNomeBeneficiarioTitularConta(finalidade);
            });
        }
        
        $(document).ready(function(){
            var mensagemErro = document.getElementById('msgException');
            if (mensagemErro === undefined || mensagemErro === null) {
                $("#rb_representanteLegal").prop("checked", false);
                $("#rb_procurador").prop("checked", false);
                limparCamposProcurador();
                limparCamposRepresentanteLegal();
                ocultarConteudoBeneficiario();
                ocultarConteudoProcurador();
                ocultarConteudoRepresentanteLegal();
                verificarInclusaoCampoFolhaProcuracao();
                verificarFinalidadeCredito();
            }
            setTimeout(()=> {
                carregarTipoBeneficiario();
                reloadTipoBeneficiario();
                criarChanges();
                reloadRadioRepresentacao();
                $("#cb_tipoBeneficiario_chosen").css("width","203");
                $("#cb_tipoBeneficiario").trigger("chosen:updated");
                removerDuplicados();
                verificarMostrarTitular();
            }, 500);
        });
        
        function verificarMostrarTitular() {
            if($("#cb_tipoFinalidade").val() === "CREDITO_CONTA_OUTRO_BANCO"){
                var podeSelecionar = document.getElementById('rb_beneficiarioTitularContaTrue');
                if (podeSelecionar !== null && podeSelecionar !== undefined && podeSelecionar.checked) {
                    $("#cpf_cnpj_titular_finalidade_credito_outros_bancos").fadeOut();
                    $("#nome_titular_finalidade_credito_outros_bancos").fadeOut();
                    var linhaPix = document.getElementById("linhaChavePixCpfCnpjBeneficiario");
                    linhaPix.style.opacity = '1';
                    $("#linhaChavePixCpfCnpjBeneficiario").fadeIn();
                } else {
                    $("#linhaChavePixCpfCnpjBeneficiario").fadeOut();
                    $("#cpf_cnpj_titular_finalidade_credito_outros_bancos").fadeIn();
                    $("#nome_titular_finalidade_credito_outros_bancos").fadeIn();
                } 
            }
        }
        
        function verificarFinalidadeCredito() {
            if ($("#cb_tipoFinalidade").val() === "CREDITO_CONTA_BB" || $("#cb_tipoFinalidade").val() === "CREDITO_CONTA_OUTRO_BANCO" || $("#cb_tipoFinalidade").val() === "PIX") {
                $("#rb_beneficiarioTitularContaTrue").prop("checked", true);
            } else {
                $("#rb_beneficiarioTitularContaTrue").prop("checked", false);
            }
        }
        
        function beneficiarioEhTitularConta(){
            if ($("#cb_tipoFinalidade").val() === "CREDITO_CONTA_BB" || $("#cb_tipoFinalidade").val() === "CREDITO_CONTA_OUTRO_BANCO" || $("#cb_tipoFinalidade").val() === "PIX") {
                $("#rb_beneficiarioTitularContaTrue").prop("checked", true);
            } else {
                $("#rb_beneficiarioTitularContaTrue").prop("checked", false);
            }
        }
        
        function carregarCpfCnpjNomeBeneficiarioTitularConta() {
            var finalidade = document.getElementById('cb_tipoFinalidade').value;
            var tipoBeneficiario = document.getElementById('cb_tipoBeneficiario').value;

            if (finalidade === "PIX" && tipoBeneficiario !== "") {

                var cpfCnpj = "";
                var nome = "";
                var beneficiarioEhIgualTitularConta = $("#rb_beneficiarioTitularContaTrue").is(':checked');

                if (beneficiarioSelecionadoDoCombo && beneficiarioEhIgualTitularConta) {

                    cpfCnpj = recuperarCpfCnpjBeneficiarioSelecionadoComMascara();
                    nome = $("#comboBeneficiario option:selected").text();
                }

                if (beneficiarioDigitadoManualmente && beneficiarioEhIgualTitularConta) {

                    cpfCnpj = $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val();
                    nome = $("#solicitacaoTransiente_beneficiario_pessoa_nome").val();
                }

                if (cpfCnpj !== "" && nome !== "") {
                    preecherCamposCpfCnpjNomeFinalidadePIX(cpfCnpj, nome);
                }
            } else {
                //console.log("Null" );
            }

        }
        
        function preencherCpfNomeQuandoTerceiros(name, cpfCnpj){
            var finalidade = document.getElementById('cb_tipoFinalidade').value;
            var beneficiarioEhIgualTitularConta = $("#rb_beneficiarioTitularContaTrue").is(':checked');
            if (finalidade === "CREDITO_CONTA_OUTRO_BANCO" && beneficiarioEhIgualTitularConta) {
                $("#finalidadeCreditoOutrosBancos_titular_nome").val(name);
                $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").val(cpfCnpj);
            }
        }
        
        function recuperarCpfCnpjBeneficiarioSelecionadoComMascara() {
            var cpfCnpj = "";
            if ($("#comboBeneficiario").val() !== "0") {
                cpfCnpj = $("#comboBeneficiario").find(':selected').attr('cpf');//01234567890 00000000000191
                cpfCnpj = mascaraCpfCnpj(cpfCnpj);
            }
            return cpfCnpj;
        }
        
        function preecherCamposCpfCnpjNomeFinalidade(cpfCnpj, nome) {
            $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").val(cpfCnpj);
            $("#finalidadeCreditoOutrosBancos_titular_nome").val(nome);
            $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").attr("readonly", "true");
            $("#finalidadeCreditoOutrosBancos_titular_nome").attr("readonly", "true");
        }
        
        //PIX
          function preecherCamposCpfCnpjNomeFinalidadePIX(cpfCnpj, nome) {
            console.log("cpf: "+$("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val());
            console.log("nome: "+$("#solicitacaoTransiente_beneficiario_pessoa_nome").val());
            $("#finalidadePIX_titular_cpfCnpj").val(cpfCnpj);
            $("#finalidadePIX_titular_nome").val(nome);
            $("#finalidadePIX_titular_nome").attr("readonly", "true");
            
            
          
            
            
        }
        
        function mascaraCpfCnpj (cpfCnpj) {
            if (cpfCnpj !== null && cpfCnpj !== undefined) {
                if (cpfCnpj.length == 11) {
                    var g1 = cpfCnpj.substring(0, 3);
                    var g2 = cpfCnpj.substring(3, 6);
                    var g3 = cpfCnpj.substring(6, 9);
                    var g4 = cpfCnpj.substring(9, 11);
                    return g1 + "." + g2 + "." + g3 + "-" + g4;
                }
                if (cpfCnpj.length == 14) {
                    var g1 = cpfCnpj.substring(0, 2);
                    var g2 = cpfCnpj.substring(2, 5);
                    var g3 = cpfCnpj.substring(5, 8);
                    var g4 = cpfCnpj.substring(8, 12);
                    var g5 = cpfCnpj.substring(12, 14);
                    return g1 + "." + g2 + "." + g3 + "/" + g4 + "-" + g5;
                }
            }
            return cpfCnpj;
        }
        
        function limparBeneficiario() {
        	var spanAvisoCPF = $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj");
        	if (spanAvisoCPF!=undefined) spanAvisoCPF.fadeOut();
            //esconderOuApresentarLinhaBeneficiarioCpfCnpj();
            limparCpfCnpjNomeSolicitacao();
            limparCpfCnpjNomeFinalidade();
            limpaElementosHiddenBeneficiario();
        }
        
        function verificarBeneficiarioSelecionado() {
           // debugger;
            if ($("#comboBeneficiario").val() !== "0") {
                $("#beneficiario").val($("#beneficiarioTransiente").val());
                preencherCampoCpfCnpj(); 
                carregarCpfCnpjNomeBeneficiarioTitularConta();
            } else {
                limparCpfCnpjNomeSolicitacao();
                limparCpfCnpjNomeFinalidade();
                limparCampoCpfCnpj();
            }
            montaComboTitularContaPIX();
        }
        

        function limparCampoCpfCnpj() {
            $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val("");
            $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").prop("disabled", false);
        }
        
        function esconderOuApresentarLinhaBeneficiarioCpfCnpj() {               
            if (isTipoBeneficiarioSelecionadoSomenteSelecao()) {
                $("#linha_beneficiario_cpfCnpj").fadeOut();
                $("#linha_beneficiario_nome").fadeOut();
                $('#lb_msg_cpf_cnpj_quantidade_digitos').css('display', 'none');
            } else {
                $("#linha_beneficiario_cpfCnpj").fadeIn();
                $("#linha_beneficiario_nome").fadeIn();
                $('#lb_msg_cpf_cnpj_quantidade_digitos').css('display', 'block');
            }
        }
               
        function isTipoBeneficiarioSelecionadoSomenteSelecao() {
              //  var tiposBeneficiariosSomenteSelecao = ['1', '5'];
            var tiposBeneficiariosSomenteSelecao = ['1', '5', '9', '10'];
            var tipoBeneficiarioSelecionado = $("#cb_tipoBeneficiario").val();
            return tiposBeneficiariosSomenteSelecao.includes(tipoBeneficiarioSelecionado);
        }
        
        function preencherCampoCpfCnpj() {
            var cpfCnpj = mascaraCpfCnpj($("#comboBeneficiario").val());
            $("#linha_beneficiario_cpfCnpj").fadeIn();
            
			// Pra qualquer das situaï¿½ï¿½es, o CPF/CNPJ deve ser desabilitado. 
          //  $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").prop("disabled", true);
			
            if (cpfCnpj) {
                $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val(cpfCnpj);
                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").fadeOut();
                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").text("");
            } else {
                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").fadeIn();
                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").text("CPF/CNPJ não informado. Retifique o cadastro da parte no processo");
            }
        }
        
        function limparCpfCnpjNomeSolicitacao() {
                $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val("");
                $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeAttr("readonly");
                $("#solicitacaoTransiente_beneficiario_pessoa_nome").val("");
                $("#solicitacaoTransiente_beneficiario_pessoa_nome").attr("readonly", "false");
        }
        
        function limparCpfCnpjNomeFinalidade() {
                $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").val("");
                $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").removeAttr("readonly");
                $("#finalidadeCreditoOutrosBancos_titular_nome").val("");
                $("#finalidadeCreditoOutrosBancos_titular_nome").attr("readonly", "true");
        }
        
        function limparCpfCnpjNomeFinalidadePIX() {
                $("#finalidadePIX_titular_cpfCnpj").val("");
                $("#finalidadePIX_titular_cpfCnpj").removeAttr("readonly");
                $("#finalidadePIX_titular_nome").val("");
                $("#finalidadePIX_titular_nome").attr("readonly", "true");
        }
        
        
        function byPassCpfCnpjBeneficiarioConta() {
            $("#solicitacaoTransiente_beneficiario_pessoa_nome").trigger("onblur");
            montaComboTitularContaPIX();
        }

        function cbTipoBeneficiarioChange(){
            limparBeneficiario();
            addChange();
        }
        
        function addChange() {
            var eventos = "validaCpfCnpj_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj();";//$("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").attr("onblur");
            eventos += "byPassCpfCnpjBeneficiarioConta();";
            $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").attr("onblur", eventos);
            $("#solicitacaoTransiente_procurador_cpfCnpj").attr("onblur", "montaComboTitularContaPIX()");
            $("#solicitacaoTransiente_representanteLegal_cpfCnpj").attr("onblur", "montaComboTitularContaPIX()");
        }
        
        function montaComboTitularContaPIX(){
            var cpf_beneficiario = $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val();
            var nm_beneficiario  = "";
            var beneficiario_selecionado = $('#comboBeneficiario').find(":selected").val();

            if(beneficiario_selecionado !== '0' && beneficiario_selecionado !== undefined){
                nm_beneficiario = $('#comboBeneficiario').find(":selected").text();
            }else{
                if(cpf_beneficiario !== undefined && cpf_beneficiario !== null && cpf_beneficiario.length > 0){
                    nm_beneficiario = recuperaNomePorCpfCnpj(cpf_beneficiario); 
                }
            }

            var select = document.querySelector('#select_titular');            
            if(select !== null){
                var cont = select.length;
                   while(select.length > 0){
                       console.log(select.length);
                          select.remove(cont--);
                   }
                select.options[select.options.length] = new Option("SELECIONE...",  "");

                //#Beneficiario    
                if(cpf_beneficiario !== undefined && cpf_beneficiario !== null && cpf_beneficiario.length > 0){
                    select.options[select.options.length] = new Option(cpf_beneficiario+" -"+ nm_beneficiario, cpf_beneficiario+" - "+ nm_beneficiario);
                 }
             }

            //#Procurador
            var cpf_procurador = $("#solicitacaoTransiente_procurador_cpfCnpj").val();
            var nm_procurador  =""; 

            if(cpf_procurador !== undefined && cpf_procurador !== null && cpf_procurador.length > 13){
                nm_procurador = recuperaNomePorCpfCnpj(cpf_procurador); 
                $("#solicitacaoTransiente\\.procurador\\.nome").val(nm_procurador);
                if(select !== null){
                    select.options[select.options.length] = new Option(cpf_procurador+" -"+ nm_procurador, cpf_procurador+" - "+ nm_procurador);
                }
             }

            //#Representante Legal
            var cpf_representante = $("#solicitacaoTransiente_representanteLegal_cpfCnpj").val();
            var nm_representante  =""; 

            if(cpf_representante !== undefined && cpf_representante !== null && cpf_representante.length > 13){
                nm_representante = recuperaNomePorCpfCnpj(cpf_representante); 
                $("#solicitacaoTransiente\\.representanteLegal\\.nome").val(nm_representante);
                if(select !== null){
                    select.options[select.options.length] = new Option(cpf_representante+" -"+ nm_representante, cpf_representante+" - "+ nm_representante);
                }
             }  
            preecherCamposTransicaoCpfCnpjNomeFinalidadePIX();  
          }
          
          function preecherCamposTransicaoCpfCnpjNomeFinalidadePIX() {
            var valorComboChavePix = $("#select_titular").val();
            if(valorComboChavePix !== undefined){
                var arrayAtributos =  valorComboChavePix.split(" - "); 

                console.log("nome: "+arrayAtributos[1]);
                $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").val(arrayAtributos[0]);
                $("#finalidadeCreditoOutrosBancos_titular_nome").val(arrayAtributos[1]);
            }
        }

        function recuperaNomePorCpfCnpj(cpfCnpj){
            var nomeUserCpf="";
            cpfCnpj = cpfCnpj.replaceAll(".", "").replaceAll("-","").replaceAll("/", "");
            //mostrarTelaCarregando();
            console.log("bloqueio de tela!");
            //const mostrarTelaCarregando = () => $("#bloqueio").addClass("escurecer");
           // const esconderTelaCarregando = () => $("#bloqueio").removeClass("escurecer");
            const retornoComSucesso = (data) => nomeUserCpf = data;

            $.ajax(
                "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validar.json",
                {
                  //  beforeSend: mostrarTelaCarregando,
                    success: retornoComSucesso,
                    dataType: "text",
                    async: false
                }
            )
           // .complete(esconderTelaCarregando);

            return nomeUserCpf;
        }
                
        function exibirLinhaCpfCnpjBeneficiario() {
            if (($("#cb_tipoFinalidade").val() === "CREDITO_CONTA_BB" || $("#cb_tipoFinalidade").val() === "CREDITO_CONTA_OUTRO_BANCO") 
            && $("#comboBeneficiario").val() !== "0") {
                var cpfCnpj = recuperarCpfCnpjBeneficiarioSelecionadoComMascara();
                $("#labelCpfCnpj").val(cpfCnpj);
                $("#linhaCpfCnpjBeneficiario").fadeIn();
            }
        }
        
        function ocultarLinhaCpfCnpjBeneficiario() {
            $("#labelCpfCnpj").val("");
            $("#linhaCpfCnpjBeneficiario").fadeOut();
        }
        
        function reloadTipoBeneficiario(){
             if($("#cb_tipoBeneficiario").val() !== "" ){
                    
                        var valor_tipo_beneficiario = $("#cb_tipoBeneficiario").val();
                        if(valor_tipo_beneficiario === "9" || valor_tipo_beneficiario === "10" || valor_tipo_beneficiario ==="11"){
                                $("#linha_beneficiario_cpfCnpj").fadeIn();
                                $("#linha_beneficiario_nome").fadeIn();
                        }
                        if(valor_tipo_beneficiario === "1" || valor_tipo_beneficiario === "5" || valor_tipo_beneficiario === "1" 
                        || valor_tipo_beneficiario === "3" || valor_tipo_beneficiario === "7" || valor_tipo_beneficiario === ""
                        || valor_tipo_beneficiario === null || valor_tipo_beneficiario === "0"){
                                
                                $("#linha_beneficiario_cpfCnpj").fadeOut();
                                $("#linha_beneficiario_nome").fadeOut();

                        }

                        var opt = $("#cb_tipoBeneficiario > option:checked");
                        var papel = opt.attr('papel');
                        abrirCombo(papel);
                        $("#linhaBeneficiario").css("opacity","1");
                     //   exibirDadosBeneficiario();
             }   
        }
        
        function carregarTipoBeneficiario(){
                $("#cb_tipoBeneficiario").val(5);
        }
        
        function criarChanges(){
                $("#rb_procurador").change(function(){ 
                        if($(this).is(':checked')){
                                exibirConteudoProcurador();
                        }else{
                                ocultarConteudoProcurador();
                                limparCamposProcurador();
                                $('#cb_estados').prop('selectedIndex',0); 
                                $('#cb_estados').trigger("chosen:updated");
                        }
                        verificarInclusaoCampoFolhaProcuracao();
                });
                
                $("#rb_representanteLegal").change(function(){
                        if($(this).is(':checked')){
                                exibirConteudoRepresentanteLegal();
                        }else{
                                ocultarConteudoRepresentanteLegal();
                                limparCamposRepresentanteLegal();
                        }
                        verificarInclusaoCampoFolhaProcuracao();
                });
                
                function changeTipoBeneficiario(){
                       limpaElementosHiddenBeneficiario()
                        var opt = $("#cb_tipoBeneficiario > option:checked");
                        var tipo = opt.attr('tipo');
                        var papel = opt.attr('papel');
                        
                        switch(tipo){
                                case "AUTOR":
                                        abrirCombo(papel);
                                       // exibirDadosBeneficiario();
                                        break;
                                
                                case "REU":
                                        abrirCombo(papel);
                                      //  exibirDadosBeneficiario();
                                        break;
                                
                                case "ADVOGADO":
                                        abrirCombo(papel);
                                      //  exibirDadosBeneficiario();
                                        break;
                                
                                case "OUTROS":
                                      comLinhaCpfNomeBeneficiario();
                                      
                                      //  exibirDadosBeneficiario();
                                        break;
                                     
                                default: 
//                                        $("#linhaBeneficiario").fadeOut();
                                        //abrirCombo(papel);
                                        //exibirDadosBeneficiario();
                                        resetBeneficiario();
                                        break;
                        }                
                }
                $("#cb_tipoBeneficiario").change(changeTipoBeneficiario);
                $("#comboBeneficiario").change(function(){
                       $("#idBeneficiario").val($("#comboBeneficiario").val());
                       ocultarConteudoBeneficiario();
//                       if($("#comboBeneficiario").val()!=="0"){
//                                ocultarConteudoBeneficiario();
//                       }else{
//                                exibirConteudoBeneficiario();
//                       }
                });
        }
        
        function limparCamposProcurador(){
                $("#solicitacaoTransiente_procurador_cpfCnpj").val("");
                $("#solicitacaoTransiente\\.procurador\\.nome").val("");
                $("#solicitacaoTransiente\\.numeroRegistroOab").val("");
                $("#solicitacaoTransiente\\.tipoRegistroOab").val("");
        }
        
        function limparCamposRepresentanteLegal(){
                $("#solicitacaoTransiente_representanteLegal_cpfCnpj").val("");
                $("#solicitacaoTransiente\\.representanteLegal\\.nome").val("");
        }
        
        function limparCampoFolhaProcuracao(){
                $('#solicitacaoTransiente\\.folhaProcuracao').val('');
        }
    
        function exibirConteudoProcurador(){
                $("#linha_procurador_cpfCnpj").fadeIn();
                $("#linha_procurador_cpfCnpj").css('opacity', '1');
                $("#linha_procurador_nome").fadeIn();
                $("#linha_procurador_nome").css('opacity', '1');
                $("#linha_procurador_registroOAB").fadeIn();
                $("#linha_procurador_registroOAB").css('opacity', '1');
                $("#linha_procurador_ufOAB").fadeIn();
                $("#linha_procurador_ufOAB").css('opacity', '1');
                $("#linha_procurador_tipoOAB").fadeIn();
                $("#linha_procurador_tipoOAB").css('opacity', '1');
                
                $("#cb_estados").chosen();
                $("#cb_estados_chosen").css("width","150");
        }
        
        function exibirConteudoRepresentanteLegal(){
                $("#linha_representanteLegal_cpfCnpj").fadeIn();
                $("#linha_representanteLegal_cpfCnpj").css('opacity', '1');
                $("#linha_representanteLegal_nome").fadeIn();
                $("#linha_representanteLegal_nome").css('opacity', '1');
        }
        
        function exibirDadosBeneficiario(){
            $("#qtdeBeneficiarios").val($('#comboBeneficiario option').size());
            
           // exibirConteudoBeneficiario();
          
                if($("#qtdeBeneficiarios").val() !== null 
                && $("#qtdeBeneficiarios").val() <= 1
                ){
                 $("#linhaBeneficiario").fadeOut();
                }else{
                   $("#linhaBeneficiario").fadeIn();
                   if($("#comboBeneficiario").val()!== null && $("#comboBeneficiario").val()!=="0"){
                           ocultarConteudoBeneficiario();
                   }
                }
                
        }
        
        function exibirConteudoBeneficiario(){
                
                $("#linha_beneficiario_cpfCnpj").fadeIn();
                $("#linha_beneficiario_nome").fadeIn();

        }    
        
        function ocultarConteudoBeneficiario(){
                $("#linha_beneficiario_cpfCnpj").fadeOut();
                $("#linha_beneficiario_nome").fadeOut();
                
                if ($("#cb_tipoBeneficiario").val() === null || $("#cb_tipoBeneficiario").val() === "0") {
                        
                        $('#solicitacaoTransiente_beneficiario_pessoa_nome').val('');
                        $('#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj').val('');
                }
        }
        
        function ocultarConteudoProcurador(){
                $("#linha_procurador_cpfCnpj").fadeOut();
                $("#linha_procurador_nome").fadeOut();
                $("#linha_procurador_registroOAB").fadeOut();
                $("#linha_procurador_ufOAB").fadeOut();
                $("#linha_procurador_tipoOAB").fadeOut();
        }
        
        function ocultarConteudoRepresentanteLegal(){ 
                $("#linha_representanteLegal_cpfCnpj").fadeOut();
                $("#linha_representanteLegal_nome").fadeOut();
        }
        
        function verificarInclusaoCampoFolhaProcuracao(){
                if(!$("#rb_procurador").is(":checked") && !$("#rb_representanteLegal").is(":checked")){
                      $("#linhaFolhaProcuracao").fadeOut();
                      limparCampoFolhaProcuracao();
                }else{
                      $("#linhaFolhaProcuracao").fadeIn();    
                }
                montaComboTitularContaPIX();
        }
        
        function reloadRadioRepresentacao(){
            if($("#rb_procurador").is(":checked")){
                    $("#rb_procurador").trigger("change");
            }
            if($("#rb_representanteLegal").is(":checked")){
                    $("#rb_representanteLegal").trigger("change");
            }
        }
        
        function abrirCombo( papel ){
                $("#linhaBeneficiario").fadeIn();
                carregarComboParte(papel);
        }
        
        function carregarComboParte(papel){ 
                $("#comboBeneficiario").html("<option value='0' selected='selected'>Selecione...</option>");
                $("#comboBeneficiario").trigger("change");  
                var url = "/portaltrtsp/pages/consulta-processual-tribunal-session/"+papel;
                if(url.length > 0){
                        $.ajax({
                                dataType: "json",
                                url: url,
                                async: false,
                                success: function(data){
                                    $("#comboBeneficiario_chosen").hide();
                                        if(data !== 'undefined' && data.length > 0) {
                                                var optionHtml = "";
                                                $.each(data,function(i,element){
                                                    var dadosBeneficiario ="";
                                                        optionHtml += "<option value='"+element.cpfCnpj+"' cpf='"+element.cpfCnpj+"' >"+ element.nome +" </option>";
                                                        dadosBeneficiario ="<input type='hidden' id='"+element.cpfCnpj+"' value='"+element.cpfCnpj+";"+element.nome+";"+element.principal+";"+papel+"'>";
                                                        document.getElementById("camposBeneficiario").innerHTML +=dadosBeneficiario;
   
                                                });
                                                $("#comboBeneficiario").append(optionHtml);
                                                if(data[0].cpfCnpj.length > 0){
                                                    comLinhaComboBeneficiario();
                                                 }else{
                                                    comLinhaCpfNomeBeneficiario();
                                                }  
                                        }else{
                                                limpaElementosHiddenBeneficiario();
                                               // $("#beneficiarioTransiente").val(null); 
                                                comLinhaCpfNomeBeneficiario();
                                             }
                                        if($("#idBeneficiario").val() !== null && $("#idBeneficiario").val()!=="0"){       
                                                $("#comboBeneficiario").val($("#idBeneficiario").val());
                                        }
                                         $("#comboBeneficiario").chosen();
                                        $("#comboBeneficiario").trigger("chosen:updated");
                                        $("#comboBeneficiario_chosen").css("width","450");      
                                }
                        });
                } 
                
        }     

        function setarHiddens(id){
            if (id !== '0' && id !== 'undefined') {
                let valorAgrupado = $("#"+id).val();
                let valordesagrupado = valorAgrupado.split(";");
                preencheElementosHiddenBeneficiario(valordesagrupado[0], //cpfcnpj
                                                    valordesagrupado[1], //nome
                                                    valordesagrupado[2],// principal
                                                    valordesagrupado[3] //papel
                                                    //valordesagrupado[$("#idProcesso").val()] //numeroProcesso
                                                 );
             } 
             
           //document.getElementById("camposBeneficiario").innerHTML = "";
             
        }
        
        function preencheElementosHiddenBeneficiario(cpfCnpj,nome,partePrincipal,papel){

            $("#beneficiario_pessoa_nome").val(nome);
            $("#beneficiario_pessoa_cpfCnpj").val(cpfCnpj);
            $("#beneficiario_parte_principal").val(partePrincipal);
            $("#beneficiario_papel").val(papel);
            $("#beneficiario_processo").val($("#idProcesso").val());
            
               carregarParteSiscondj(cpfCnpj,partePrincipal,papel,$("#idProcesso").val());
              
        }
        
        function limpaElementosHiddenBeneficiario(){

            $("#comboBeneficiario").val('0');
            $("#beneficiario_pessoa_nome").val('');
            $("#beneficiario_pessoa_cpfCnpj").val('');
            $("#beneficiario_parte_principal").val('');
            $("#beneficiario_papel").val('');
            $("#beneficiario_processo").val('');
            $("#beneficiario_id").val('0'); 
            
           // document.getElementById("camposBeneficiario").innerHTML = "";
        }
        
          function carregarParteSiscondj(cpfCnpj,partePrincipal,papel,processo){ 
                var url = "/portaltrtsp/pages/verifica-parte-processo/"+cpfCnpj+"/"+partePrincipal+"/"+papel+"/"+processo;                       
                if(url.length > 0){
                        $.ajax({
                            dataType: "json",
                            url: url,
                            async: false,
                            success: function(data){
                                if(data !== 'undefined') {
                                        $("#beneficiario_id").val(data);
                                }else{
                                        $("#beneficiario_id").val('0'); 
                                    }  
                                }
                        });
                    }   
                }     

        
        
         function comLinhaComboBeneficiario(){
              
            $("#linhaBeneficiario").fadeIn();
            $("#comboBeneficiario_chosen").show();
            ocultarConteudoBeneficiario();
        }
        
        function comLinhaCpfNomeBeneficiario(){
            $("#linhaBeneficiario").fadeOut();
            exibirConteudoBeneficiario(); 
        }
        
        function resetBeneficiario(){
                removerDuplicados();
                $("#linhaBeneficiario").fadeOut();
                 ocultarConteudoBeneficiario();
                 $("#cb_tipoBeneficiario").val("").trigger("chosen:updated"); 
                 //removerDuplicados();
            }
            
            function removerDuplicados() {
                let elementos = document.querySelectorAll("#comboBeneficiario_chosen"); // Seleciona todos os itens duplicados
                if(elementos.length > 0)
                    for (let i = 1; i < elementos.length; i++) { // Mantï¿½m o primeiro, remove os outros
                        elementos[i].remove();
                    }
            }
        
        
          //PIX
    function verificaStatus(valor){
           console.log("verificaStatus(param)");
           var tp_finalidade = document.getElementById('cb_tipoFinalidade').value;
        if(tp_finalidade == "PIX"){
            if(valor==='N'){
                document.getElementById("text_cpfcnpjtitularconta").style.display= '';
                document.getElementById("combo_cpfcnpjtitularconta").style.display= 'none';
                document.getElementById("finalidadePIX_titular_cpfCnpj").value= '';
                 document.getElementById("finalidadePIX_titular_nome").value= '';
            }else{
                document.getElementById("titularesConta").selected="selected";
                document.getElementById("finalidadePIX_titular_nome").value= '';
                document.getElementById("combo_cpfcnpjtitularconta").style.display= '';
                document.getElementById("text_cpfcnpjtitularconta").style.display= 'none';
            }
        }else{
            console.log("No pix");
        }
    }

</script>

<tr class="finalidade_credito_conta_bb">
	<td class="titulo">Tipo de Crédito*</td>
	<td>
		<select id="cb_tipoCredito" name="finalidadeCreditoEmContaBB.contaBancaria.tipo" style="min-width: 150px; display: none;" onchange="eventoChangeTipoCredito();">
			<option value="">Selecione...</option>
			<option value="CONTA_CORRENTE">Conta Corrente</option><option value="CONTA_POUPANCA">Conta Poupança</option>
		</select><div class="chosen-container chosen-container-single" style="width: 150px;" title="" id="cb_tipoCredito_chosen"><a class="chosen-single" tabindex="-1"><span>Conta Corrente</span><div><b></b></div></a><div class="chosen-drop"><div class="chosen-search"><input type="text" autocomplete="off"></div><ul class="chosen-results"><li class="active-result result-selected" style="" data-option-array-index="0">Selecione...</li><li class="active-result result-selected" style="" data-option-array-index="1">Conta Corrente</li><li class="active-result" style="" data-option-array-index="2">Conta Poupança</li></ul></div></div>
                
	</td>
</tr>

<tr class="finalidade_credito_conta_bb">
	<td class="titulo">Agência (Sem Dígito Verificador)*</td>
	<td>
    	<input id="finalidadeCreditoEmContaBB.contaBancaria.agencia" name="finalidadeCreditoEmContaBB.contaBancaria.agencia" onkeypress="Mascara(this,Integer);" onkeyup="Mascara(this,Integer);limparMensagemErro('error.finalidade.agencia')" onkeydown="Mascara(this,Integer);" type="text" value="" size="4" maxlength="4">
        
    </td>
</tr>

<tr class="finalidade_credito_conta_bb">
	<td class="titulo">Número da Conta*</td>
	<td>
                <input id="finalidadeCreditoEmContaBB.contaBancaria.conta" name="finalidadeCreditoEmContaBB.contaBancaria.conta" onkeypress="Mascara(this,Integer);" onkeyup="Mascara(this,Integer);limparMensagemErro('error.finalidade.conta')" onkeydown="Mascara(this,Integer);" type="text" value="" size="11" maxlength="11">
                

                -
                <input id="digitoVerificadorBB" name="finalidadeCreditoEmContaBB.contaBancaria.digitoVerificador" onkeyup="limparMensagemErro('error.finalidade.digitoVerificador')" type="text" value="" size="1" maxlength="1">
                <label style="color:#555555; font-size:10px;">(Quando o dígito verificador for a letra 'X',informe 'X')</label>
                
        </td>
</tr>

<tr id="finalidade_credito_conta_bb_poupanca" style="display: none;">
    <td class="titulo">Variação da Poupança*</td>
    <td>
    	<select id="variacaoPoupanca" name="finalidadeCreditoEmContaBB.contaBancaria.variacaoPoupanca" style="min-width: 100px; display: none;">
			<option value="">Selecione...</option>
			<option value="POUPANCA_OURO">51 - Poupança Ouro</option><option value="POUPANCA_OURO_SALARIO">52 - Poupança Ouro Salário</option><option value="POUPANCA_POUPEX">96 - Poupança Poupex</option><option value="POUPANCA_POUPEX_SALARIO">97 - Poupança Poupex Salário</option><option value="BANCO_POSTAL">61 - Banco Postal</option>
	</select><div class="chosen-container chosen-container-single" style="width: 180px;" title="" id="variacaoPoupanca_chosen"><a class="chosen-single" tabindex="-1"><span>Selecione...</span><div><b></b></div></a><div class="chosen-drop"><div class="chosen-search"><input type="text" autocomplete="off"></div><ul class="chosen-results"></ul></div></div>
    	    	
    </td>
</tr>














<script type="text/javascript">
        
        $(document).ready(function(){
            initReload();
        });
        
        function configurarCamposTipoResgate() {
            
            var tipoResgate = $("#cb_tipoResgate").val();
            
            if (tipoResgate !== null && tipoResgate !== "") {

                exibirLinhasTipoResgate();
            } else {
                esconderLinhasTipoResgate();
            }
        }
        
        function selecionarTipoResgate() {
            
            var tipoResgate = $("#cb_tipoResgate").val();
            
            if (tipoResgate === "RESGATE_VALOR_REAL_INFORMADO") {
                $("#valor_real").val("");
                $("#rb_comCorrecao").prop("checked", false);
                $("#rb_semCorrecao").prop("checked", false);
                $("#rb_semCorrecao").prop("disabled", false);
                //$("#valor_real").removeAttr("readonly");
                
                if (!($("#cb_tipoFinalidade").val() === "GRU" || $("#cb_tipoFinalidade").val() === "GPS" || $("#cb_tipoFinalidade").val() === "DARF")) {
                    $("#valor_real").removeAttr('readOnly');
                }
            }

            if (tipoResgate === "RESGATE_VALOR_TOTAL") {
                $("#rb_comCorrecao").prop("checked", true);
                $("#rb_semCorrecao").prop("checked", false);
                $("#rb_semCorrecao").prop("disabled", true);
                $("#valor_real").attr("readonly", true);
                selecionarContaComParcelaSelecionada();
            }
            
            configurarCamposTipoResgate();
        }
        
        function exibirLinhasTipoResgate() {
            $("#linhaValorSolicitacao").fadeIn();
            $("#linhaValorLevantamento").fadeIn();
        }
        
        function esconderLinhasTipoResgate() {
            $("#linhaValorSolicitacao").fadeOut();
            $("#linhaValorLevantamento").fadeOut();
        }
        
        function criarMascara(){
               $(".mascara_valor").maskMoney({
                        thousands: '.',
                        decimal: ','
                }); 
        }
    
        function initReload(){
            criarMascara();
            configurarCamposTipoResgate();
        }
        
</script>
<tr id="linhaTipoResgate" class="finalidade_credito_conta_bb">
        <td class="titulo">
                Tipo de Resgate*
        </td>
        <td>
                <select id="cb_tipoResgate" name="solicitacaoTransiente.tipoQualificador" onchange="selecionarTipoResgate();" style="display: none;">
                         <option value="">Selecione...</option>
                         <option value="RESGATE_VALOR_REAL_INFORMADO">Valor Real Informado</option><option value="RESGATE_VALOR_TOTAL">Valor Total da Conta </option>
                </select><div class="chosen-container chosen-container-single" style="width: 235px;" title="" id="cb_tipoResgate_chosen"><a class="chosen-single" tabindex="-1"><span>Selecione...</span><div><b></b></div></a><div class="chosen-drop"><div class="chosen-search"><input type="text" autocomplete="off"></div><ul class="chosen-results"><li class="active-result result-selected" style="" data-option-array-index="0">Selecione...</li><li class="active-result" style="" data-option-array-index="1">Valor Real Informado</li><li class="active-result" style="" data-option-array-index="2">Valor Total da Conta </li></ul></div></div>
                
        </td>
        
</tr>
<tr id="linhaValorSolicitacao" class="finalidade_credito_conta_bb" style="opacity: 1; display: none;">
        <td class="titulo">
                Valor (R$)*
        </td>
        <td>
                <input id="valor_real" name="solicitacaoTransiente.valorReal" class="mascara_valor" type="text" value="0,00" size="40" maxlength="20"> 
                (Do valor informado poderão ser descontados impostos e taxas.)
                
                
        </td>
</tr>
<tr id="linhaValorLevantamento" class="finalidade_credito_conta_bb" style="opacity: 1; display: none;">
        <td class="titulo">
                Valor do Levantamento*
        </td>
        <td>
                <input id="rb_comCorrecao" name="solicitacaoTransiente.baseCalculo" type="radio" value="COM_ACRESCIMO"> 
                Com Correção 
                <input id="rb_semCorrecao" name="solicitacaoTransiente.baseCalculo" type="radio" value="SEM_ACRESCIMO"> 
                Sem Correção
                
        </td>
        
</tr>

<script type="text/javascript">
        
        $(document).ready(function(){
                if($("#cb_tipoCredito").val() === "CONTA_CORRENTE"){
                        $("#finalidade_credito_conta_bb_poupanca").fadeOut();
                }else{
                        if($("#cb_tipoCredito").val() === "CONTA_POUPANCA"){
                             $("#finalidade_credito_conta_bb_poupanca").fadeIn();   
                        }
                }
        });
        
        //Permitir apenas inserï¿½ï¿½o da letra x para caracteres alfabï¿½ticos
        $("#digitoVerificadorBB").on({change:function(){
                        verificarDigito();         
                },keypress:function(event){
                        verificarTecla(event);
                },keydown:function(event){
                        verificarTecla(event);         
                },keyup:function(event){
                        verificarTecla(event);         
                }});
        
        function verificarTecla(event){
                var key = (event.which) ? event.which : event.keyCode;
                if(key>=65 && key<=90 && key!==88){
                        if($("#digitoVerificadorBB").val().length>0){
                                $("#digitoVerificadorBB").val('');   
                        }
                }
        }
        function verificarDigito(){
                var digito =  $("#digitoVerificadorBB").val();
                if(digito!=='x' && digito!=='X' && !$.isNumeric(digito)){
                        $("#digitoVerificadorBB").val('');   
                }else if(digito==='x'){
                        $("#digitoVerificadorBB").val('X');   
                }
        }
</script>
                                        
                                        
                                        
                                        
                                        
                                        
                                        
                                         
                                        
                                
                        
                
                        
                                
                                        
                                        
                                        
                                        
                                                



























<!-- Formulario de selecao de autor e reu

OBS: Passar o nome da classe via jsp:param.
-->










    
    

    
        
        
        
        

    
        

    

    
<script type="text/javascript">
    
    function carregarListaPix(){
        var combo = document.getElementById('pixDi1namico');

        if (combo !== null && combo !== undefined){ 
            for (a in combo.options) { combo.options.remove(a); }
        }

        var podeSelecionar = document.getElementById('rb_beneficiarioTitularContaFalse').checked;

        if(!podeSelecionar){
            $("#linhaChavePixDinamico").fadeOut();
            $("#linhaChavePixCpfCnpjBeneficiario").fadeIn();
            
            var cpfCnpj = $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val();
            var nome = $("#solicitacaoTransiente_beneficiario_pessoa_nome").val();

            preecherCamposCpfCnpjNomeFinalidadePIX(cpfCnpj, nome);
            
            return;
                
        }
        
        $("#linhaChavePixDinamico").fadeIn();
        $("#linhaChavePixCpfCnpjBeneficiario").fadeOut();

        var beneficiario = document.getElementById('solicitacaoTransiente_beneficiario_pessoa_cpfCnpj').value;

        var procurador = document.getElementById('solicitacaoTransiente_procurador_cpfCnpj').value;

        var representante = document.getElementById('solicitacaoTransiente_representanteLegal_cpfCnpj').value;



        combo.appendChild(new Option('Selecione','selecione'));
        
        if(beneficiario !== null && beneficiario.trim().length !== 0){
            combo.appendChild(new Option(beneficiario,beneficiario));
        }

        if(procurador !== null && procurador.trim().length !== 0){
            combo.appendChild(new Option(procurador,procurador));
        }
        
        if(representante !== null && representante.trim().length !== 0){
            combo.appendChild(new Option(representante,representante));
        }
        
        
        combo.addEventListener('change', function handle(event){
            var selectElement = event.target;
            var value = selectElement.value;    
            
            
            var value2 = combo.options[combo.selectedIndex].value;
            var text2 = combo.options[combo.selectedIndex].text;
            
            preecherCamposCpfCnpjNomeFinalidadePIX(value2, text2);
            
        });
    }
    
        var finalidade = document.getElementById('cb_tipoFinalidade').value;
        
        if (finalidade === "CREDITO_CONTA_BB" || finalidade === "CREDITO_CONTA_OUTRO_BANCO" || finalidade === "PIX") {
            document.getElementById('rb_beneficiarioTitularContaFalse').addEventListener('click', function(e){  
                limparCpfCnpjNomeFinalidade();
            });

            document.getElementById('rb_beneficiarioTitularContaTrue').addEventListener('click', function(e){  
                carregarCpfCnpjNomeBeneficiarioTitularConta(finalidade);
            });
        }
        
        $(document).ready(function(){
            var mensagemErro = document.getElementById('msgException');
            if (mensagemErro === undefined || mensagemErro === null) {
                $("#rb_representanteLegal").prop("checked", false);
                $("#rb_procurador").prop("checked", false);
                limparCamposProcurador();
                limparCamposRepresentanteLegal();
                ocultarConteudoBeneficiario();
                ocultarConteudoProcurador();
                ocultarConteudoRepresentanteLegal();
                verificarInclusaoCampoFolhaProcuracao();
                verificarFinalidadeCredito();
            }
            setTimeout(()=> {
                carregarTipoBeneficiario();
                reloadTipoBeneficiario();
                criarChanges();
                reloadRadioRepresentacao();
                $("#cb_tipoBeneficiario_chosen").css("width","203");
                $("#cb_tipoBeneficiario").trigger("chosen:updated");
                removerDuplicados();
                verificarMostrarTitular();
            }, 500);
        });
        
        function verificarMostrarTitular() {
            if($("#cb_tipoFinalidade").val() === "CREDITO_CONTA_OUTRO_BANCO"){
                var podeSelecionar = document.getElementById('rb_beneficiarioTitularContaTrue');
                if (podeSelecionar !== null && podeSelecionar !== undefined && podeSelecionar.checked) {
                    $("#cpf_cnpj_titular_finalidade_credito_outros_bancos").fadeOut();
                    $("#nome_titular_finalidade_credito_outros_bancos").fadeOut();
                    var linhaPix = document.getElementById("linhaChavePixCpfCnpjBeneficiario");
                    linhaPix.style.opacity = '1';
                    $("#linhaChavePixCpfCnpjBeneficiario").fadeIn();
                } else {
                    $("#linhaChavePixCpfCnpjBeneficiario").fadeOut();
                    $("#cpf_cnpj_titular_finalidade_credito_outros_bancos").fadeIn();
                    $("#nome_titular_finalidade_credito_outros_bancos").fadeIn();
                } 
            }
        }
        
        function verificarFinalidadeCredito() {
            if ($("#cb_tipoFinalidade").val() === "CREDITO_CONTA_BB" || $("#cb_tipoFinalidade").val() === "CREDITO_CONTA_OUTRO_BANCO" || $("#cb_tipoFinalidade").val() === "PIX") {
                $("#rb_beneficiarioTitularContaTrue").prop("checked", true);
            } else {
                $("#rb_beneficiarioTitularContaTrue").prop("checked", false);
            }
        }
        
        function beneficiarioEhTitularConta(){
            if ($("#cb_tipoFinalidade").val() === "CREDITO_CONTA_BB" || $("#cb_tipoFinalidade").val() === "CREDITO_CONTA_OUTRO_BANCO" || $("#cb_tipoFinalidade").val() === "PIX") {
                $("#rb_beneficiarioTitularContaTrue").prop("checked", true);
            } else {
                $("#rb_beneficiarioTitularContaTrue").prop("checked", false);
            }
        }
        
        function carregarCpfCnpjNomeBeneficiarioTitularConta() {
            var finalidade = document.getElementById('cb_tipoFinalidade').value;
            var tipoBeneficiario = document.getElementById('cb_tipoBeneficiario').value;

            if (finalidade === "PIX" && tipoBeneficiario !== "") {

                var cpfCnpj = "";
                var nome = "";
                var beneficiarioEhIgualTitularConta = $("#rb_beneficiarioTitularContaTrue").is(':checked');

                if (beneficiarioSelecionadoDoCombo && beneficiarioEhIgualTitularConta) {

                    cpfCnpj = recuperarCpfCnpjBeneficiarioSelecionadoComMascara();
                    nome = $("#comboBeneficiario option:selected").text();
                }

                if (beneficiarioDigitadoManualmente && beneficiarioEhIgualTitularConta) {

                    cpfCnpj = $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val();
                    nome = $("#solicitacaoTransiente_beneficiario_pessoa_nome").val();
                }

                if (cpfCnpj !== "" && nome !== "") {
                    preecherCamposCpfCnpjNomeFinalidadePIX(cpfCnpj, nome);
                }
            } else {
                //console.log("Null" );
            }

        }
        
        function preencherCpfNomeQuandoTerceiros(name, cpfCnpj){
            var finalidade = document.getElementById('cb_tipoFinalidade').value;
            var beneficiarioEhIgualTitularConta = $("#rb_beneficiarioTitularContaTrue").is(':checked');
            if (finalidade === "CREDITO_CONTA_OUTRO_BANCO" && beneficiarioEhIgualTitularConta) {
                $("#finalidadeCreditoOutrosBancos_titular_nome").val(name);
                $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").val(cpfCnpj);
            }
        }
        
        function recuperarCpfCnpjBeneficiarioSelecionadoComMascara() {
            var cpfCnpj = "";
            if ($("#comboBeneficiario").val() !== "0") {
                cpfCnpj = $("#comboBeneficiario").find(':selected').attr('cpf');//01234567890 00000000000191
                cpfCnpj = mascaraCpfCnpj(cpfCnpj);
            }
            return cpfCnpj;
        }
        
        function preecherCamposCpfCnpjNomeFinalidade(cpfCnpj, nome) {
            $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").val(cpfCnpj);
            $("#finalidadeCreditoOutrosBancos_titular_nome").val(nome);
            $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").attr("readonly", "true");
            $("#finalidadeCreditoOutrosBancos_titular_nome").attr("readonly", "true");
        }
        
        //PIX
          function preecherCamposCpfCnpjNomeFinalidadePIX(cpfCnpj, nome) {
            console.log("cpf: "+$("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val());
            console.log("nome: "+$("#solicitacaoTransiente_beneficiario_pessoa_nome").val());
            $("#finalidadePIX_titular_cpfCnpj").val(cpfCnpj);
            $("#finalidadePIX_titular_nome").val(nome);
            $("#finalidadePIX_titular_nome").attr("readonly", "true");
            
            
          
            
            
        }
        
        function mascaraCpfCnpj (cpfCnpj) {
            if (cpfCnpj !== null && cpfCnpj !== undefined) {
                if (cpfCnpj.length == 11) {
                    var g1 = cpfCnpj.substring(0, 3);
                    var g2 = cpfCnpj.substring(3, 6);
                    var g3 = cpfCnpj.substring(6, 9);
                    var g4 = cpfCnpj.substring(9, 11);
                    return g1 + "." + g2 + "." + g3 + "-" + g4;
                }
                if (cpfCnpj.length == 14) {
                    var g1 = cpfCnpj.substring(0, 2);
                    var g2 = cpfCnpj.substring(2, 5);
                    var g3 = cpfCnpj.substring(5, 8);
                    var g4 = cpfCnpj.substring(8, 12);
                    var g5 = cpfCnpj.substring(12, 14);
                    return g1 + "." + g2 + "." + g3 + "/" + g4 + "-" + g5;
                }
            }
            return cpfCnpj;
        }
        
        function limparBeneficiario() {
        	var spanAvisoCPF = $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj");
        	if (spanAvisoCPF!=undefined) spanAvisoCPF.fadeOut();
            //esconderOuApresentarLinhaBeneficiarioCpfCnpj();
            limparCpfCnpjNomeSolicitacao();
            limparCpfCnpjNomeFinalidade();
            limpaElementosHiddenBeneficiario();
        }
        
        function verificarBeneficiarioSelecionado() {
           // debugger;
            if ($("#comboBeneficiario").val() !== "0") {
                $("#beneficiario").val($("#beneficiarioTransiente").val());
                preencherCampoCpfCnpj(); 
                carregarCpfCnpjNomeBeneficiarioTitularConta();
            } else {
                limparCpfCnpjNomeSolicitacao();
                limparCpfCnpjNomeFinalidade();
                limparCampoCpfCnpj();
            }
            montaComboTitularContaPIX();
        }
        

        function limparCampoCpfCnpj() {
            $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val("");
            $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").prop("disabled", false);
        }
        
        function esconderOuApresentarLinhaBeneficiarioCpfCnpj() {               
            if (isTipoBeneficiarioSelecionadoSomenteSelecao()) {
                $("#linha_beneficiario_cpfCnpj").fadeOut();
                $("#linha_beneficiario_nome").fadeOut();
                $('#lb_msg_cpf_cnpj_quantidade_digitos').css('display', 'none');
            } else {
                $("#linha_beneficiario_cpfCnpj").fadeIn();
                $("#linha_beneficiario_nome").fadeIn();
                $('#lb_msg_cpf_cnpj_quantidade_digitos').css('display', 'block');
            }
        }
               
        function isTipoBeneficiarioSelecionadoSomenteSelecao() {
              //  var tiposBeneficiariosSomenteSelecao = ['1', '5'];
            var tiposBeneficiariosSomenteSelecao = ['1', '5', '9', '10'];
            var tipoBeneficiarioSelecionado = $("#cb_tipoBeneficiario").val();
            return tiposBeneficiariosSomenteSelecao.includes(tipoBeneficiarioSelecionado);
        }
        
        function preencherCampoCpfCnpj() {
            var cpfCnpj = mascaraCpfCnpj($("#comboBeneficiario").val());
            $("#linha_beneficiario_cpfCnpj").fadeIn();
            
			// Pra qualquer das situaï¿½ï¿½es, o CPF/CNPJ deve ser desabilitado. 
          //  $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").prop("disabled", true);
			
            if (cpfCnpj) {
                $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val(cpfCnpj);
                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").fadeOut();
                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").text("");
            } else {
                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").fadeIn();
                $("#span_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").text("CPF/CNPJ não informado. Retifique o cadastro da parte no processo");
            }
        }
        
        function limparCpfCnpjNomeSolicitacao() {
                $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val("");
                $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").removeAttr("readonly");
                $("#solicitacaoTransiente_beneficiario_pessoa_nome").val("");
                $("#solicitacaoTransiente_beneficiario_pessoa_nome").attr("readonly", "false");
        }
        
        function limparCpfCnpjNomeFinalidade() {
                $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").val("");
                $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").removeAttr("readonly");
                $("#finalidadeCreditoOutrosBancos_titular_nome").val("");
                $("#finalidadeCreditoOutrosBancos_titular_nome").attr("readonly", "true");
        }
        
        function limparCpfCnpjNomeFinalidadePIX() {
                $("#finalidadePIX_titular_cpfCnpj").val("");
                $("#finalidadePIX_titular_cpfCnpj").removeAttr("readonly");
                $("#finalidadePIX_titular_nome").val("");
                $("#finalidadePIX_titular_nome").attr("readonly", "true");
        }
        
        
        function byPassCpfCnpjBeneficiarioConta() {
            $("#solicitacaoTransiente_beneficiario_pessoa_nome").trigger("onblur");
            montaComboTitularContaPIX();
        }

        function cbTipoBeneficiarioChange(){
            limparBeneficiario();
            addChange();
        }
        
        function addChange() {
            var eventos = "validaCpfCnpj_solicitacaoTransiente_beneficiario_pessoa_cpfCnpj();";//$("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").attr("onblur");
            eventos += "byPassCpfCnpjBeneficiarioConta();";
            $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").attr("onblur", eventos);
            $("#solicitacaoTransiente_procurador_cpfCnpj").attr("onblur", "montaComboTitularContaPIX()");
            $("#solicitacaoTransiente_representanteLegal_cpfCnpj").attr("onblur", "montaComboTitularContaPIX()");
        }
        
        function montaComboTitularContaPIX(){
            var cpf_beneficiario = $("#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj").val();
            var nm_beneficiario  = "";
            var beneficiario_selecionado = $('#comboBeneficiario').find(":selected").val();

            if(beneficiario_selecionado !== '0' && beneficiario_selecionado !== undefined){
                nm_beneficiario = $('#comboBeneficiario').find(":selected").text();
            }else{
                if(cpf_beneficiario !== undefined && cpf_beneficiario !== null && cpf_beneficiario.length > 0){
                    nm_beneficiario = recuperaNomePorCpfCnpj(cpf_beneficiario); 
                }
            }

            var select = document.querySelector('#select_titular');            
            if(select !== null){
                var cont = select.length;
                   while(select.length > 0){
                       console.log(select.length);
                          select.remove(cont--);
                   }
                select.options[select.options.length] = new Option("SELECIONE...",  "");

                //#Beneficiario    
                if(cpf_beneficiario !== undefined && cpf_beneficiario !== null && cpf_beneficiario.length > 0){
                    select.options[select.options.length] = new Option(cpf_beneficiario+" -"+ nm_beneficiario, cpf_beneficiario+" - "+ nm_beneficiario);
                 }
             }

            //#Procurador
            var cpf_procurador = $("#solicitacaoTransiente_procurador_cpfCnpj").val();
            var nm_procurador  =""; 

            if(cpf_procurador !== undefined && cpf_procurador !== null && cpf_procurador.length > 13){
                nm_procurador = recuperaNomePorCpfCnpj(cpf_procurador); 
                $("#solicitacaoTransiente\\.procurador\\.nome").val(nm_procurador);
                if(select !== null){
                    select.options[select.options.length] = new Option(cpf_procurador+" -"+ nm_procurador, cpf_procurador+" - "+ nm_procurador);
                }
             }

            //#Representante Legal
            var cpf_representante = $("#solicitacaoTransiente_representanteLegal_cpfCnpj").val();
            var nm_representante  =""; 

            if(cpf_representante !== undefined && cpf_representante !== null && cpf_representante.length > 13){
                nm_representante = recuperaNomePorCpfCnpj(cpf_representante); 
                $("#solicitacaoTransiente\\.representanteLegal\\.nome").val(nm_representante);
                if(select !== null){
                    select.options[select.options.length] = new Option(cpf_representante+" -"+ nm_representante, cpf_representante+" - "+ nm_representante);
                }
             }  
            preecherCamposTransicaoCpfCnpjNomeFinalidadePIX();  
          }
          
          function preecherCamposTransicaoCpfCnpjNomeFinalidadePIX() {
            var valorComboChavePix = $("#select_titular").val();
            if(valorComboChavePix !== undefined){
                var arrayAtributos =  valorComboChavePix.split(" - "); 

                console.log("nome: "+arrayAtributos[1]);
                $("#finalidadeCreditoOutrosBancos_titular_cpfCnpj").val(arrayAtributos[0]);
                $("#finalidadeCreditoOutrosBancos_titular_nome").val(arrayAtributos[1]);
            }
        }

        function recuperaNomePorCpfCnpj(cpfCnpj){
            var nomeUserCpf="";
            cpfCnpj = cpfCnpj.replaceAll(".", "").replaceAll("-","").replaceAll("/", "");
            //mostrarTelaCarregando();
            console.log("bloqueio de tela!");
            //const mostrarTelaCarregando = () => $("#bloqueio").addClass("escurecer");
           // const esconderTelaCarregando = () => $("#bloqueio").removeClass("escurecer");
            const retornoComSucesso = (data) => nomeUserCpf = data;

            $.ajax(
                "/portaltrtsp/pages/cpfcnpj/"+cpfCnpj+"/validar.json",
                {
                  //  beforeSend: mostrarTelaCarregando,
                    success: retornoComSucesso,
                    dataType: "text",
                    async: false
                }
            )
           // .complete(esconderTelaCarregando);

            return nomeUserCpf;
        }
                
        function exibirLinhaCpfCnpjBeneficiario() {
            if (($("#cb_tipoFinalidade").val() === "CREDITO_CONTA_BB" || $("#cb_tipoFinalidade").val() === "CREDITO_CONTA_OUTRO_BANCO") 
            && $("#comboBeneficiario").val() !== "0") {
                var cpfCnpj = recuperarCpfCnpjBeneficiarioSelecionadoComMascara();
                $("#labelCpfCnpj").val(cpfCnpj);
                $("#linhaCpfCnpjBeneficiario").fadeIn();
            }
        }
        
        function ocultarLinhaCpfCnpjBeneficiario() {
            $("#labelCpfCnpj").val("");
            $("#linhaCpfCnpjBeneficiario").fadeOut();
        }
        
        function reloadTipoBeneficiario(){
             if($("#cb_tipoBeneficiario").val() !== "" ){
                    
                        var valor_tipo_beneficiario = $("#cb_tipoBeneficiario").val();
                        if(valor_tipo_beneficiario === "9" || valor_tipo_beneficiario === "10" || valor_tipo_beneficiario ==="11"){
                                $("#linha_beneficiario_cpfCnpj").fadeIn();
                                $("#linha_beneficiario_nome").fadeIn();
                        }
                        if(valor_tipo_beneficiario === "1" || valor_tipo_beneficiario === "5" || valor_tipo_beneficiario === "1" 
                        || valor_tipo_beneficiario === "3" || valor_tipo_beneficiario === "7" || valor_tipo_beneficiario === ""
                        || valor_tipo_beneficiario === null || valor_tipo_beneficiario === "0"){
                                
                                $("#linha_beneficiario_cpfCnpj").fadeOut();
                                $("#linha_beneficiario_nome").fadeOut();

                        }

                        var opt = $("#cb_tipoBeneficiario > option:checked");
                        var papel = opt.attr('papel');
                        abrirCombo(papel);
                        $("#linhaBeneficiario").css("opacity","1");
                     //   exibirDadosBeneficiario();
             }   
        }
        
        function carregarTipoBeneficiario(){
                $("#cb_tipoBeneficiario").val();
        }
        
        function criarChanges(){
                $("#rb_procurador").change(function(){ 
                        if($(this).is(':checked')){
                                exibirConteudoProcurador();
                        }else{
                                ocultarConteudoProcurador();
                                limparCamposProcurador();
                                $('#cb_estados').prop('selectedIndex',0); 
                                $('#cb_estados').trigger("chosen:updated");
                        }
                        verificarInclusaoCampoFolhaProcuracao();
                });
                
                $("#rb_representanteLegal").change(function(){
                        if($(this).is(':checked')){
                                exibirConteudoRepresentanteLegal();
                        }else{
                                ocultarConteudoRepresentanteLegal();
                                limparCamposRepresentanteLegal();
                        }
                        verificarInclusaoCampoFolhaProcuracao();
                });
                
                function changeTipoBeneficiario(){
                       limpaElementosHiddenBeneficiario()
                        var opt = $("#cb_tipoBeneficiario > option:checked");
                        var tipo = opt.attr('tipo');
                        var papel = opt.attr('papel');
                        
                        switch(tipo){
                                case "AUTOR":
                                        abrirCombo(papel);
                                       // exibirDadosBeneficiario();
                                        break;
                                
                                case "REU":
                                        abrirCombo(papel);
                                      //  exibirDadosBeneficiario();
                                        break;
                                
                                case "ADVOGADO":
                                        abrirCombo(papel);
                                      //  exibirDadosBeneficiario();
                                        break;
                                
                                case "OUTROS":
                                      comLinhaCpfNomeBeneficiario();
                                      
                                      //  exibirDadosBeneficiario();
                                        break;
                                     
                                default: 
//                                        $("#linhaBeneficiario").fadeOut();
                                        //abrirCombo(papel);
                                        //exibirDadosBeneficiario();
                                        resetBeneficiario();
                                        break;
                        }                
                }
                $("#cb_tipoBeneficiario").change(changeTipoBeneficiario);
                $("#comboBeneficiario").change(function(){
                       $("#idBeneficiario").val($("#comboBeneficiario").val());
                       ocultarConteudoBeneficiario();
//                       if($("#comboBeneficiario").val()!=="0"){
//                                ocultarConteudoBeneficiario();
//                       }else{
//                                exibirConteudoBeneficiario();
//                       }
                });
        }
        
        function limparCamposProcurador(){
                $("#solicitacaoTransiente_procurador_cpfCnpj").val("");
                $("#solicitacaoTransiente\\.procurador\\.nome").val("");
                $("#solicitacaoTransiente\\.numeroRegistroOab").val("");
                $("#solicitacaoTransiente\\.tipoRegistroOab").val("");
        }
        
        function limparCamposRepresentanteLegal(){
                $("#solicitacaoTransiente_representanteLegal_cpfCnpj").val("");
                $("#solicitacaoTransiente\\.representanteLegal\\.nome").val("");
        }
        
        function limparCampoFolhaProcuracao(){
                $('#solicitacaoTransiente\\.folhaProcuracao').val('');
        }
    
        function exibirConteudoProcurador(){
                $("#linha_procurador_cpfCnpj").fadeIn();
                $("#linha_procurador_cpfCnpj").css('opacity', '1');
                $("#linha_procurador_nome").fadeIn();
                $("#linha_procurador_nome").css('opacity', '1');
                $("#linha_procurador_registroOAB").fadeIn();
                $("#linha_procurador_registroOAB").css('opacity', '1');
                $("#linha_procurador_ufOAB").fadeIn();
                $("#linha_procurador_ufOAB").css('opacity', '1');
                $("#linha_procurador_tipoOAB").fadeIn();
                $("#linha_procurador_tipoOAB").css('opacity', '1');
                
                $("#cb_estados").chosen();
                $("#cb_estados_chosen").css("width","150");
        }
        
        function exibirConteudoRepresentanteLegal(){
                $("#linha_representanteLegal_cpfCnpj").fadeIn();
                $("#linha_representanteLegal_cpfCnpj").css('opacity', '1');
                $("#linha_representanteLegal_nome").fadeIn();
                $("#linha_representanteLegal_nome").css('opacity', '1');
        }
        
        function exibirDadosBeneficiario(){
            $("#qtdeBeneficiarios").val($('#comboBeneficiario option').size());
            
           // exibirConteudoBeneficiario();
          
                if($("#qtdeBeneficiarios").val() !== null 
                && $("#qtdeBeneficiarios").val() <= 1
                ){
                 $("#linhaBeneficiario").fadeOut();
                }else{
                   $("#linhaBeneficiario").fadeIn();
                   if($("#comboBeneficiario").val()!== null && $("#comboBeneficiario").val()!=="0"){
                           ocultarConteudoBeneficiario();
                   }
                }
                
        }
        
        function exibirConteudoBeneficiario(){
                
                $("#linha_beneficiario_cpfCnpj").fadeIn();
                $("#linha_beneficiario_nome").fadeIn();

        }    
        
        function ocultarConteudoBeneficiario(){
                $("#linha_beneficiario_cpfCnpj").fadeOut();
                $("#linha_beneficiario_nome").fadeOut();
                
                if ($("#cb_tipoBeneficiario").val() === null || $("#cb_tipoBeneficiario").val() === "0") {
                        
                        $('#solicitacaoTransiente_beneficiario_pessoa_nome').val('');
                        $('#solicitacaoTransiente_beneficiario_pessoa_cpfCnpj').val('');
                }
        }
        
        function ocultarConteudoProcurador(){
                $("#linha_procurador_cpfCnpj").fadeOut();
                $("#linha_procurador_nome").fadeOut();
                $("#linha_procurador_registroOAB").fadeOut();
                $("#linha_procurador_ufOAB").fadeOut();
                $("#linha_procurador_tipoOAB").fadeOut();
        }
        
        function ocultarConteudoRepresentanteLegal(){ 
                $("#linha_representanteLegal_cpfCnpj").fadeOut();
                $("#linha_representanteLegal_nome").fadeOut();
        }
        
        function verificarInclusaoCampoFolhaProcuracao(){
                if(!$("#rb_procurador").is(":checked") && !$("#rb_representanteLegal").is(":checked")){
                      $("#linhaFolhaProcuracao").fadeOut();
                      limparCampoFolhaProcuracao();
                }else{
                      $("#linhaFolhaProcuracao").fadeIn();    
                }
                montaComboTitularContaPIX();
        }
        
        function reloadRadioRepresentacao(){
            if($("#rb_procurador").is(":checked")){
                    $("#rb_procurador").trigger("change");
            }
            if($("#rb_representanteLegal").is(":checked")){
                    $("#rb_representanteLegal").trigger("change");
            }
        }
        
        function abrirCombo( papel ){
                $("#linhaBeneficiario").fadeIn();
                carregarComboParte(papel);
        }
        
        function carregarComboParte(papel){ 
                $("#comboBeneficiario").html("<option value='0' selected='selected'>Selecione...</option>");
                $("#comboBeneficiario").trigger("change");  
                var url = "/portaltrtsp/pages/consulta-processual-tribunal-session/"+papel;
                if(url.length > 0){
                        $.ajax({
                                dataType: "json",
                                url: url,
                                async: false,
                                success: function(data){
                                    $("#comboBeneficiario_chosen").hide();
                                        if(data !== 'undefined' && data.length > 0) {
                                                var optionHtml = "";
                                                $.each(data,function(i,element){
                                                    var dadosBeneficiario ="";
                                                        optionHtml += "<option value='"+element.cpfCnpj+"' cpf='"+element.cpfCnpj+"' >"+ element.nome +" </option>";
                                                        dadosBeneficiario ="<input type='hidden' id='"+element.cpfCnpj+"' value='"+element.cpfCnpj+";"+element.nome+";"+element.principal+";"+papel+"'>";
                                                        document.getElementById("camposBeneficiario").innerHTML +=dadosBeneficiario;
   
                                                });
                                                $("#comboBeneficiario").append(optionHtml);
                                                if(data[0].cpfCnpj.length > 0){
                                                    comLinhaComboBeneficiario();
                                                 }else{
                                                    comLinhaCpfNomeBeneficiario();
                                                }  
                                        }else{
                                                limpaElementosHiddenBeneficiario();
                                               // $("#beneficiarioTransiente").val(null); 
                                                comLinhaCpfNomeBeneficiario();
                                             }
                                        if($("#idBeneficiario").val() !== null && $("#idBeneficiario").val()!=="0"){       
                                                $("#comboBeneficiario").val($("#idBeneficiario").val());
                                        }
                                         $("#comboBeneficiario").chosen();
                                        $("#comboBeneficiario").trigger("chosen:updated");
                                        $("#comboBeneficiario_chosen").css("width","450");      
                                }
                        });
                } 
                
        }     

        function setarHiddens(id){
            if (id !== '0' && id !== 'undefined') {
                let valorAgrupado = $("#"+id).val();
                let valordesagrupado = valorAgrupado.split(";");
                preencheElementosHiddenBeneficiario(valordesagrupado[0], //cpfcnpj
                                                    valordesagrupado[1], //nome
                                                    valordesagrupado[2],// principal
                                                    valordesagrupado[3] //papel
                                                    //valordesagrupado[$("#idProcesso").val()] //numeroProcesso
                                                 );
             } 
             
           //document.getElementById("camposBeneficiario").innerHTML = "";
             
        }
        
        function preencheElementosHiddenBeneficiario(cpfCnpj,nome,partePrincipal,papel){

            $("#beneficiario_pessoa_nome").val(nome);
            $("#beneficiario_pessoa_cpfCnpj").val(cpfCnpj);
            $("#beneficiario_parte_principal").val(partePrincipal);
            $("#beneficiario_papel").val(papel);
            $("#beneficiario_processo").val($("#idProcesso").val());
            
               carregarParteSiscondj(cpfCnpj,partePrincipal,papel,$("#idProcesso").val());
              
        }
        
        function limpaElementosHiddenBeneficiario(){

            $("#comboBeneficiario").val('0');
            $("#beneficiario_pessoa_nome").val('');
            $("#beneficiario_pessoa_cpfCnpj").val('');
            $("#beneficiario_parte_principal").val('');
            $("#beneficiario_papel").val('');
            $("#beneficiario_processo").val('');
            $("#beneficiario_id").val('0'); 
            
           // document.getElementById("camposBeneficiario").innerHTML = "";
        }
        
          function carregarParteSiscondj(cpfCnpj,partePrincipal,papel,processo){ 
                var url = "/portaltrtsp/pages/verifica-parte-processo/"+cpfCnpj+"/"+partePrincipal+"/"+papel+"/"+processo;                       
                if(url.length > 0){
                        $.ajax({
                            dataType: "json",
                            url: url,
                            async: false,
                            success: function(data){
                                if(data !== 'undefined') {
                                        $("#beneficiario_id").val(data);
                                }else{
                                        $("#beneficiario_id").val('0'); 
                                    }  
                                }
                        });
                    }   
                }     

        
        
         function comLinhaComboBeneficiario(){
              
            $("#linhaBeneficiario").fadeIn();
            $("#comboBeneficiario_chosen").show();
            ocultarConteudoBeneficiario();
        }
        
        function comLinhaCpfNomeBeneficiario(){
            $("#linhaBeneficiario").fadeOut();
            exibirConteudoBeneficiario(); 
        }
        
        function resetBeneficiario(){
                removerDuplicados();
                $("#linhaBeneficiario").fadeOut();
                 ocultarConteudoBeneficiario();
                 $("#cb_tipoBeneficiario").val("").trigger("chosen:updated"); 
                 //removerDuplicados();
            }
            
            function removerDuplicados() {
                let elementos = document.querySelectorAll("#comboBeneficiario_chosen"); // Seleciona todos os itens duplicados
                if(elementos.length > 0)
                    for (let i = 1; i < elementos.length; i++) { // Mantï¿½m o primeiro, remove os outros
                        elementos[i].remove();
                    }
            }
        
        
          //PIX
    function verificaStatus(valor){
           console.log("verificaStatus(param)");
           var tp_finalidade = document.getElementById('cb_tipoFinalidade').value;
        if(tp_finalidade == "PIX"){
            if(valor==='N'){
                document.getElementById("text_cpfcnpjtitularconta").style.display= '';
                document.getElementById("combo_cpfcnpjtitularconta").style.display= 'none';
                document.getElementById("finalidadePIX_titular_cpfCnpj").value= '';
                 document.getElementById("finalidadePIX_titular_nome").value= '';
            }else{
                document.getElementById("titularesConta").selected="selected";
                document.getElementById("finalidadePIX_titular_nome").value= '';
                document.getElementById("combo_cpfcnpjtitularconta").style.display= '';
                document.getElementById("text_cpfcnpjtitularconta").style.display= 'none';
            }
        }else{
            console.log("No pix");
        }
    }

</script>





















<script>
        $(document).ready(function () {
                $("#periodoApuracao").datepicker();
                $("#dataVencimento").datepicker();

                $(".mascara_valor").maskMoney({
                        thousands: '.',
                        decimal: ',',
                        allowZero: true
                });
                $("#valor_real").attr("readOnly", true);
        });

        function verificarValorPrincipal() {
                var valorPrincipal = $("#valorPrincipal").val();
                var valor = valorPrincipal.replace(/[^0-9]/g, "");
                if (valor > 0) {
                        somarValorPrincipal();
                }
        }

        function somarValorPrincipal() {
                var valorMulta = $("#valorMulta").val().replace(/\./g, "");//retira mascara para soma
                if(valorMulta!==''){
                        valorMulta = parseFloat(valorMulta.replace(/\,/g, "."));//utiliza '.' na conversao para float
                }else{
                        valorMulta=0;
                }
                
                var valorJuros = $("#valorJuros").val().replace(/\./g, "");
                if(valorJuros!==''){
                        valorJuros = parseFloat(valorJuros.replace(/\,/g, "."));
                }else{
                        valorJuros=0;
                }
                
                var valorPrincipal = $("#valorPrincipal").val().replace(/\./g, "");
                if(valorPrincipal!==''){
                        valorPrincipal = parseFloat(valorPrincipal.replace(/\,/g, "."));
                }else{
                        valorPrincipal=0;
                }
                var total = 0;
                total = valorMulta+valorJuros+valorPrincipal;
                $("#valor_real").val(Valor(total.toFixed(2)));//converte e arredonda o resultado
                
                if(valorMulta>0 || valorJuros>0){
                        $('input:radio[name=solicitacaoTransiente\\.baseCalculo]:nth(1)').prop('checked',true);//sem correcao
                        $('#rb_comCorrecao').prop('disabled', true);
                }else{
                        $('input:radio[name=solicitacaoTransiente\\.baseCalculo]').prop('checked',false);//sem correcao
                        $('#rb_comCorrecao').prop('disabled', false);
                }
        }
</script>
                                        
                                        
                                        
                                        
                                        
                                         
                                        
                                
                        
                
                        
                
                                
                        </tbody>
                        
                                <tfoot>
                                        <tr>
                                                <td class="act_td" colspan="2">
                                                        <span class="bt_acessibilidade" title="Adicionar">
                                                                
                                                                        





















<input type="button" id="bt_add_solicitacao" class="botaoNovo" value="" onclick="executarAcao_bt_add_solicitacao()">

<script type="text/javascript">

	function executarAcao_bt_add_solicitacao(){
				
                
	            var retorno = true;

                
                        retorno = validarRequisicoesPendentes(false);
                
        
                
                        
                if(retorno) {
                        
                                
                                        $("#form_alvara").attr("action","/portaltrtsp/pages/mandado/pagamento/gerarSolicitacao");
                                        $("#form_alvara").submit();
                                 
                        
                }
	}
</script>

                                                                
                                                        </span>
                                                </td>
                                        </tr>
                                </tfoot>
                        
                </table>


ATENÇÃO! Qdo o alvará for para o perito, só colocamos o CPF; o nome, o sistema puxa sozinho.


ALVARÁ PARA ADVOGADO DO AUTOR OU RÉU

Ao escolher o advogado do autor, o sistema me apresenta o nome dele. Após eu escolher, aí o CPF vem automaticamente. 

Se a conta, nos dados, for de pessoa física, selecionamos que o advogado é o titular da conta; se for conta jurídica, selecionar representante legal. 




ALVARÁ DE CUSTAS

* pagamento de GRU - custas
Beneficiária é sempre a reclamada. 
 Contribuinte é a parte responsável pelo recolhimento.
 Gestão e Unidade Gestora são preenchidos automaticamente.
 Informar o valor histórico calculado e selecionar “com correção”.

ALVARÁ DE IMPOSTO DE RENDA


* pagamento IR - DARF
Contribuinte é o autor (repetir em beneficiário).
 Código 1889
 Nº de referência: CPF do recte
 Data de apuração: do depósito.
 Data de vencimento: último dia do mês corrente.
 Valor principal: o valor a ser transferido –  selecionar “com correção”
