import Image from 'next/image';

export default function LogoCards() {
	return (
		<div className='container mx-auto px-4 mt-16'>
			<div className='grid grid-cols-1 md:grid-cols-4 gap-5'>
				{/* Primeiro card */}
				<div className='flex justify-center items-center h-[160px] bg-[#27272c] rounded-lg'>
					<Image
						src='/ufs_principal_positiva.png'
						alt='ufs'
						width={138}
						height={70}
						className='filter brightness-0 invert-[0.35] transition duration-300 hover:invert-[0.25]'
					/>
				</div>

				{/* Segundo card */}
				<div className='flex justify-center items-center h-[160px] bg-[#27272c] rounded-lg'>
					<Image
						src='/ufs_principal_positiva.png'
						alt='Logo 2'
						width={138}
						height={70}
						className='filter brightness-0 invert-[0.35] transition duration-300 hover:invert-[0.25]'
					/>
				</div>

				{/* Terceiro card */}
				<div className='flex justify-center items-center h-[160px] bg-[#27272c] rounded-lg'>
					<Image
						src='/ufs_principal_positiva.png'
						alt='Logo 3'
						width={138}
						height={70}
						className='filter brightness-0 invert-[0.35] transition duration-300 hover:invert-[0.25]'
					/>
				</div>

				{/* Quarto card */}
				<div className='flex justify-center items-center h-[160px] bg-[#27272c] rounded-lg'>
					<Image
						src='/ufs_principal_positiva.png'
						alt='Logo 4'
						width={138}
						height={70}
						className='filter brightness-0 invert-[0.35] transition duration-300 hover:invert-[0.25]'
					/>
				</div>

				{/* Quinto card */}
				<div className='flex justify-center items-center h-[160px] bg-[#27272c] rounded-lg'>
					<Image
						src='/ufs_principal_positiva.png'
						alt='Logo 5'
						width={138}
						height={70}
						className='filter brightness-0 invert-[0.35] transition duration-300 hover:invert-[0.25]'
					/>
				</div>

				{/* Sexto card */}
				<div className='flex justify-center items-center h-[160px] bg-[#27272c] rounded-lg'>
					<Image
						src='/ufs_principal_positiva.png'
						alt='Logo 6'
						width={138}
						height={70}
						className='filter brightness-0 invert-[0.35] transition duration-300 hover:invert-[0.25]'
					/>
				</div>

				{/* Sétimo card */}
				<div className='flex justify-center items-center h-[160px] bg-[#27272c] rounded-lg'>
					<Image
						src='/ufs_principal_positiva.png'
						alt='Logo 7'
						width={138}
						height={70}
						className='filter brightness-0 invert-[0.35] transition duration-300 hover:invert-[0.25]'
					/>
				</div>

				{/* Oitavo card */}
				<div className='flex justify-center items-center h-[160px] bg-[#27272c] rounded-lg'>
					<Image
						src='/ufs_principal_positiva.png'
						alt='Logo 8'
						width={138}
						height={70}
						className='filter brightness-0 invert-[0.35] transition duration-300 hover:invert-[0.25]'
					/>
				</div>
			</div>
		</div>
	);
}
