import LogoSaber from '../LogoSaber';

export default function PromoContainer() {
	return (
		<div className='relative flex text-[#303030]'>
			<div className='relative flex justify-end w-1/2'>
				<div className='w-full max-w-[calc(1344px/2)]'>
					<div className='flex flex-col justify-center items-start max-w-[436px] self-end bg-[#fff] py-[120px] px-[30px]'>
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
							className='mb-[30px] text-center font-[lexend] bg-[#cf13a3] border-0 inline-block no-underline font-semibold text-white text-[16px] leading-6 !rounded-xl
 cursor-pointer !px-8 !py-3 h-auto !tracking-[0]'
						>
							{' '}
							Saiba mais sobre Valoração Tecnológica
						</a>
						<a
							href='/'
							className='mb-[30px] text-center font-[lexend] bg-[#595fef] border-0 inline-block no-underline font-semibold text-white text-[16px] leading-6 !rounded-xl
 cursor-pointer !px-8 !py-3 h-auto !tracking-[0]'
						>
							Saiba mais sobre Repartição de Benefícios
						</a>
					</div>
				</div>
			</div>
			<div
				className='flex flex-col justify-center items-center w-1/2'
				style={{
					background:
						"linear-gradient(180deg,#222228 0,rgba(34,34,40,.8) 100%),url('/futuro-sustentavel.jpg')",
					backgroundSize: 'cover',
					backgroundPosition: 'center',
				}}
			>
				<LogoSaber />
			</div>
		</div>
	);
}
