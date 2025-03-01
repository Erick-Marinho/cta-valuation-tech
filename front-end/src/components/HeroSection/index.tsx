'use client';

export default function HeroSection() {
	return (
		<section
			className='bg-center pt-[200px] pb-[120px] h-[60vh] flex items-center'
			style={{
				backgroundImage:
					'linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.7)), url("/header-cta.jpg")',
				backgroundSize: 'cover',
				backgroundPosition: 'center 60%',
			}}
		>
			<div className='container mx-auto px-4 text-center'>
				<div className='max-w-[800px] mx-auto'>
					<h1 className='text-base md:text-base lg:text-base mb-4 text-white font-[lexend] font-bold'>
						AVALIE E LUCRE COM A SOCIOBIODIVERSIDADE
					</h1>
					<h2 className='text-[40px] font-[lexend] text-white font-semibold'>
						Calcule royalties sustentáveis e gere valor para a biodiversidade
					</h2>
				</div>
			</div>
		</section>
	);
}
