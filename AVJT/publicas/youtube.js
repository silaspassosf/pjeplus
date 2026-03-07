function youtubeCriarQuadro(
	ancestral = '',
	video = '',
	titulo = ''
){
	if(!video) return
	//let imagem = 'https://img.youtube.com/vi/'+video+'/0.jpg'
	let quadro = criar('iframe','avjt-youtube','',ancestral)
	quadro.width = '560'
	quadro.height = '315'
	quadro.src = 'https://www.youtube.com/embed/' + video
	quadro.title = titulo
	quadro.frameborder = '0'
	quadro.allow = 'clipboard-write;encrypted-media;picture-in-picture;allowfullscreen'
	quadro.allowfullscreen = true
}