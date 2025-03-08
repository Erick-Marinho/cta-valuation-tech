export default function LogoSaber() {
	return (
		<div className='w-full h-full flex flex-col items-center justify-center py-16 px-8 relative overflow-hidden'>
			{/* Conteúdo do logo */}
			<div className='relative z-10 flex flex-col items-center'>
				{/* Logo SABER no estilo do PROMO */}
				<div className='text-white font-extrabold text-center'>
					<div
						className='text-9xl tracking-wide leading-none'
						style={{ fontFamily: 'Arial, sans-serif' }}
					>
						SA
					</div>
					<div
						className='text-9xl tracking-wide leading-none -mt-6'
						style={{ fontFamily: 'Lexend, sans-serif' }}
					>
						BER.
					</div>
				</div>
			</div>
			<div className='block font-[lexend] text-[#fff] font-normal text-[16px] text-center leading-5 opacity-[0.5] py-4'>
				Ferramenta de valoração de tecnologias e repartição de benefícios para
				um futuro sustentável
			</div>
		</div>
	);
}
