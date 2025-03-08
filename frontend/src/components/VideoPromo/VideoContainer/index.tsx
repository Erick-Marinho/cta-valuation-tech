export default function VideoContainer() {
	return (
		<div className='w-[1344px] max-w-[1344px] flex justify-between m-auto '>
			<div className='video-container w-[calc((100%/12)*8-(8*16px))]'>
				<div className='relative pt-[56.25%]'>
					<iframe
						className='absolute top-0 left-0 w-full h-full border-0 rounded-lg'
						src='https://www.youtube.com/embed/_WitUPMuAWw'
						title='YouTube video player'
						allow='accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture'
						allowFullScreen
					>
						Your browser does not support the video tag.
					</iframe>
				</div>
			</div>
			<div className='flex flex-col max-w-[436px] justify-center items-start px-[30px] py-0'>
				<h2 className='font-normal text-[28px] leading-9 pb-8 text-[#FFF] font-[lexend]'>
					Valorize tecnologias com acesso ao Patrimônio Genético Nacional e
					Conhecimentos Tradicionais
				</h2>
				<div className='text-white text-[16px] leading-[22px] font-normal font-[lexend] mb-[30px]'>
					Adote nossa ferramenta CTA Value Tech e nossa equipe especializada
					trabalhará constantemente para garantir processos justos de valoração
					tecnológica considerando a biodiversidade brasileira. Nossa
					metodologia engloba indicadores de sustentabilidade em quatro
					dimensões: contexto social, gestão ambiental, governança e parceria
					comercial. Você assegura práticas sustentáveis enquanto calculamos os
					royalties da sociobiodiversidade de forma ética. Descubra como nossa
					ferramenta pode fortalecer sua gestão de ESG e Compliance.
				</div>
				<button className='bg-transparent hover:bg-amber-50 text-white hover:text-[#222228] border-2 border-white hover:border-amber-50 font-medium py-3 px-8 rounded-md transition duration-300'>
					Conheça nossa metodologia
				</button>
			</div>
		</div>
	);
}
