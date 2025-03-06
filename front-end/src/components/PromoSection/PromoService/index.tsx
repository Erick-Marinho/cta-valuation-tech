import { CardService } from './CardService';

export default function PromoService() {
	const services = [
		{
			id: 1,
			icon: (
				<svg
					xmlns='http://www.w3.org/2000/svg'
					width='24'
					height='24'
					viewBox='0 0 24 24'
					fill='none'
					stroke='#222228'
					strokeWidth='2'
					strokeLinecap='round'
					strokeLinejoin='round'
				>
					<rect width='16' height='16' x='4' y='4' rx='2' />
					<path d='M9 10h6' />
					<path d='M12 7v6' />
					<path d='M7 19h1' />
					<path d='M11 19h2' />
					<path d='M16 19h1' />
				</svg>
			),
			title: 'Valoração de Tecnologias com PGN',
			description:
				'Por meio de nossa ferramenta CTA Value Tech, realizamos a valoração precisa de tecnologias que acessam o Patrimônio Genético Nacional, garantindo que você obtenha cálculos de royalties justos e transparentes para todos os envolvidos.',
			buttonText: 'Valoração Tecnológica',
		},
		{
			id: 2,
			icon: (
				<svg
					xmlns='http://www.w3.org/2000/svg'
					width='24'
					height='24'
					viewBox='0 0 24 24'
					fill='none'
					stroke='#222228'
					strokeWidth='2'
					strokeLinecap='round'
					strokeLinejoin='round'
				>
					<rect width='8' height='8' x='2' y='2' rx='2' />
					<path d='M14 2c1.1 0 2 .9 2 2v4c0 1.1-.9 2-2 2' />
					<path d='M20 2c1.1 0 2 .9 2 2v4c0 1.1-.9 2-2 2' />
					<rect width='8' height='8' x='2' y='14' rx='2' />
					<path d='M14 14c1.1 0 2 .9 2 2v4c0 1.1-.9 2-2 2' />
					<path d='M20 14c1.1 0 2 .9 2 2v4c0 1.1-.9 2-2 2' />
				</svg>
			),
			title: 'Consultoria em Compliance e ESG',
			description:
				'Deixe-nos construir uma estratégia completa envolvendo as principais diretrizes de sustentabilidade, gestão ambiental e governança para sua empresa que utiliza recursos da biodiversidade.',
			buttonText: 'Consultoria & ESG',
		},
		{
			id: 3,
			icon: (
				<svg
					xmlns='http://www.w3.org/2000/svg'
					width='24'
					height='24'
					viewBox='0 0 24 24'
					fill='none'
					stroke='#222228'
					strokeWidth='2'
					strokeLinecap='round'
					strokeLinejoin='round'
				>
					<path d='M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z' />
					<path d='m22 22-2-2' />
					<path d='M7 11 l2 2 l7 -7' />
				</svg>
			),
			title: 'Diagnóstico de Sustentabilidade',
			description:
				'Nossos especialistas avaliam sua operação considerando as 04 dimensões de avaliação, garantindo que seus processos estejam alinhados com os princípios da Convenção sobre a Diversidade Biológica.',
			buttonText: 'Diagnóstico Ambiental',
		},
		{
			id: 4,
			icon: (
				<svg
					xmlns='http://www.w3.org/2000/svg'
					width='24'
					height='24'
					viewBox='0 0 24 24'
					fill='none'
					stroke='#222228'
					strokeWidth='2'
					strokeLinecap='round'
					strokeLinejoin='round'
				>
					<path d='M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2' />
					<circle cx='9' cy='7' r='4' />
					<path d='M23 21v-2a4 4 0 0 0-3-3.87' />
					<path d='M16 3.13a4 4 0 0 1 0 7.75' />
				</svg>
			),
			title: 'Gestão de Repartição de Benefícios',
			description:
				'Nossa equipe dedicada de consultores ajuda a construir relações éticas com comunidades tradicionais e a implementar processos transparentes de repartição de benefícios para sua organização.',
			buttonText: 'Desenvolvimento Comunitário',
		},
	];

	return (
		<div
			className='relative py-[120px] pb-[240px] px-0 overflow-hidden'
			style={{
				background:
					"linear-gradient(rgba(0,0,0,0.85), rgba(0,0,0,0.95)), url('/futuro-sustentavel.jpg')",
				backgroundSize: 'cover',
				backgroundPosition: 'center',
				backgroundAttachment: 'fixed',
			}}
		>
			{/* Triângulo decorativo superior esquerdo (amarelo/âmbar) */}
			<div
				className='absolute top-0 left-0'
				style={{
					width: 0,
					height: 0,
					borderStyle: 'solid',
					borderWidth: '100px 100px 0 0',
					borderColor:
						'rgba(245, 158, 11, 0.7) transparent transparent transparent',
					transform: 'rotate(0deg)',
				}}
			></div>

			{/* Triângulo decorativo inferior direito (verde) */}
			<div
				className='absolute bottom-0 right-0'
				style={{
					width: 0,
					height: 0,
					borderStyle: 'solid',
					borderWidth: '0 0 100px 100px',
					borderColor:
						'transparent transparent rgba(16, 185, 129, 0.7) transparent',
					transform: 'rotate(0deg)',
				}}
			></div>

			<div className='container relative flex flex-col justify-center items-center w-[1344px] max-w-[1344px] m-auto'>
				<div className='block text-center'>
					<h2 className='block font-normal text-[28px] pt-0 px-[30px] pb-[120px] leading-9 m-0 font-[lexend] [margin-block-start:0.83em] [margin-block-end:0.83em] [margin-inline-start:0px] [margin-inline-end:0px] text-center text-white relative inline-block'>
						Aqui está uma pequena seleção de nossos serviços
						<span className='absolute bottom-[110px] left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#10b981] to-transparent'></span>
					</h2>
					<div className='flex justify-between text-center gap-4'>
						{services.map((service, index) => (
							<CardService
								key={service.id}
								icon={service.icon}
								title={service.title}
								description={service.description}
								buttonText={service.buttonText}
								index={index}
							/>
						))}
					</div>
				</div>
			</div>
		</div>
	);
}
