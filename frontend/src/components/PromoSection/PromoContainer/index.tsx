'use client';

import { useEffect, useRef } from 'react';
import LogoSaber from '../LogoSaber';

export default function PromoContainer() {
	const promoContentRef = useRef(null);

	useEffect(() => {
		const timer = setTimeout(() => {
			if (promoContentRef.current) {
				(promoContentRef.current as HTMLElement).classList.add('revealed');
			}
		}, 300);

		return () => clearTimeout(timer);
	}, []);

	return (
		<div className='relative flex text-[#303030]'>
			{/* Estilos simplificados inline para evitar problemas */}
			<style jsx>{`
				.promo-content {
					opacity: 0;
					transform: translateY(20px);
					transition: opacity 0.6s ease-out, transform 0.6s ease-out;
				}

				.promo-content.revealed {
					opacity: 1;
					transform: translateY(0);
				}

				.button-highlight:hover {
					transform: translateY(-2px);
					box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
					transition: transform 0.3s ease, box-shadow 0.3s ease;
				}

				.decorative-dot {
					width: 8px;
					height: 8px;
					border-radius: 50%;
					position: absolute;
				}

				.decorative-line {
					height: 60px;
					width: 1px;
					position: absolute;
					background: linear-gradient(to bottom, #10b981, transparent);
				}
			`}</style>

			<div className='relative flex justify-end w-1/2'>
				{/* Elementos decorativos simples */}
				<div
					className='decorative-dot'
					style={{ top: '20%', left: '20%', background: '#f59e0b' }}
				></div>
				<div
					className='decorative-dot'
					style={{ top: '30%', left: '30%', background: '#10b981' }}
				></div>
				<div
					className='decorative-dot'
					style={{ top: '80%', left: '40%', background: '#f59e0b' }}
				></div>
				<div
					className='decorative-line'
					style={{ top: '10%', left: '25%' }}
				></div>
				<div
					className='decorative-line'
					style={{
						top: '60%',
						left: '35%',
						background: 'linear-gradient(to bottom, #f59e0b, transparent)',
					}}
				></div>

				<div className='w-full max-w-[calc(1344px/2)]'>
					<div
						ref={promoContentRef}
						className='flex flex-col justify-center items-start max-w-[436px] self-end bg-[#FFFCF5] py-[120px] px-[30px] promo-content relative'
					>
						{/* Barra decorativa superior */}
						<div
							className='absolute top-0 left-0 w-full h-2'
							style={{
								background: 'linear-gradient(to right, #10b981, #f59e0b)',
							}}
						></div>

						{/* Decoração lateral */}
						<div
							className='absolute left-0 top-1/4 bottom-1/4 w-1'
							style={{
								background:
									'linear-gradient(to bottom, transparent, #10b981, transparent)',
							}}
						></div>

						<h2 className='block text-[28px] font-normal pb-[30px] leading-9 m-0 p-0 text-[#303030] font-[lexend] [margin-block-start:0.83em] [margin-block-end:0.83em] [margin-inline-start:0px] [margin-inline-end:0px]'>
							Nossas equipes de Valoração de Tecnologias e Gestão da
							Sociobiodiversidade estão prontas para ajudá-lo
						</h2>
						<div className='mb-[30px] text-normal text-[#303030] text-[16px] font-[lexend] leading-6'>
							O CTA Value Tech oferece uma gama de serviços personalizados que
							ajudam empresas e organizações a valorar tecnologias com acesso ao
							Patrimônio Genético Nacional de forma sustentável e ética. Seja
							implementando processos de repartição de benefícios, avaliando
							indicadores de sustentabilidade em suas quatro dimensões ou
							obtendo orientação de nossos experientes consultores que trabalham
							com os princípios da Convenção sobre a Diversidade Biológica -
							estamos aqui para ajudar.
						</div>
						<a
							href='/'
							className='mb-[30px] text-center font-[lexend] bg-[#f59e0b] border-0 inline-block no-underline font-semibold text-white text-[16px] leading-6 !rounded-xl cursor-pointer !px-8 !py-3 h-auto !tracking-[0] button-highlight'
						>
							Saiba mais sobre Valoração Tecnológica
						</a>
						<a
							href='/'
							className='mb-[30px] text-center font-[lexend] bg-[#10b981] border-0 inline-block no-underline font-semibold text-white text-[16px] leading-6 !rounded-xl cursor-pointer !px-8 !py-3 h-auto !tracking-[0] button-highlight'
						>
							Saiba mais sobre Repartição de Benefícios
						</a>

						{/* Elementos decorativos de canto */}
						<div
							className='absolute bottom-5 right-5 w-20 h-20'
							style={{
								border: '1px solid #f59e0b',
								borderRadius: '50%',
								opacity: 0.4,
							}}
						></div>

						<div
							className='absolute bottom-10 right-10 w-10 h-10'
							style={{
								border: '1px solid #10b981',
								borderRadius: '50%',
								opacity: 0.7,
							}}
						></div>
					</div>
				</div>
			</div>

			<div
				className='flex flex-col justify-center items-center w-1/2 relative'
				style={{
					background:
						"linear-gradient(180deg,#222228 0,rgba(34,34,40,.8) 100%),url('/futuro-sustentavel.jpg')",
					backgroundSize: 'cover',
					backgroundPosition: 'center',
				}}
			>
				{/* Elementos decorativos simples para a parte direita */}
				<div
					className='absolute top-10 left-10'
					style={{
						width: '40px',
						height: '40px',
						border: '1px solid rgba(255,255,255,0.3)',
						borderRadius: '4px',
						transform: 'rotate(45deg)',
					}}
				></div>

				<div
					className='absolute bottom-10 right-10'
					style={{
						width: '60px',
						height: '60px',
						border: '1px solid rgba(255,255,255,0.2)',
						borderRadius: '50%',
					}}
				></div>

				{/* Grade de pontos simples */}
				<div
					className='absolute inset-0'
					style={{
						backgroundImage:
							'radial-gradient(rgba(255,255,255,0.1) 1px, transparent 1px)',
						backgroundSize: '20px 20px',
						opacity: 0.3,
					}}
				></div>

				<LogoSaber />
			</div>
		</div>
	);
}
