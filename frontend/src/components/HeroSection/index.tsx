'use client';

export default function HeroSection() {
	return (
		<section
			className='bg-center pt-[180px] pb-[180px] flex flex-col items-center justify-center text-center'
			style={{
				background:
					'linear-gradient(180deg, #222228 0, rgba(34,34,40,0) 100%), url("/header-cta.jpg") center',
				backgroundSize: 'cover',
				backgroundPosition: 'center 60%',
			}}
		>
			<div className='relative flex flex-col justify-center items-center text-center w-[1344px] max-w-[1344px] mt-5 min-h-[35vh] m-auto px-4 '>
				<h1 className='block font-bold tracking-tight text-[100%] m-0 p-0 [margin-inline-start:0px] [margin-inline-end:0px] text-white'>
					AVALIE E LUCRE COM A SOCIOBIODIVERSIDADE
				</h1>
				<h2 className='block w-[590px] text-[40px] leading-12 text-center font-semibold mt-[30px] mb-[60px] p-0 [margin-block-start:0.83em] [margin-block-end:0.83em] [margin-inline-start:0px] [margin-inline-end:0px] text-white'>
					Calcule royalties sustentáveis e gere valor para a biodiversidade
				</h2>
			</div>
		</section>
	);
}
