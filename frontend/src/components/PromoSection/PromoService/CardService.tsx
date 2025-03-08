import { Button } from '@/components/ui/button';
import {
	Card,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle,
} from '@/components/ui/card';
import React from 'react';

export function CardService({
	icon,
	title,
	description,
	buttonText,
	index,
}: {
	icon: React.ReactNode;
	title: string;
	description: string;
	buttonText: string;
	index: number;
}) {
	// Alternating button colors (green and yellow)
	const buttonColors =
		index % 2 === 0
			? 'bg-[#f59e0b] hover:bg-[#d87706]' // yellow/amber
			: 'bg-[#10b981] hover:bg-[#059669]'; // green

	return (
		<Card className='relative flex flex-col justify-between w-[calc((100%-(16px*3))/4)] rounded-xl backdrop-blur-[20px] pt-[60px] px-5 pb-[30px] shadow-[0_3px_5px_#0000001a] bg-[#121212] text-white text-center group overflow-hidden'>
			{/* Decorative dot in the top left */}
			<div className='absolute top-3 left-3 w-2 h-2 rounded-full bg-white opacity-50'></div>

			{/* Decorative line in the top right */}
			<div className='absolute top-0 right-5 w-px h-8 bg-gradient-to-b from-transparent via-white to-transparent opacity-30'></div>

			<CardHeader className='flex items-center'>
				<div className='bg-amber-50 h-12 w-12 rounded-full flex items-center justify-center shadow-[0_0_15px_rgba(255,255,255,0.15)]'>
					{icon}
				</div>
				<CardTitle className='block text-2xl text-center font-[lexend] pb-[30px] font-normal text-[20px] leading-7 m-0 p-0 [margin-block-start:1em] [margin-block-end:1em] [margin-inline-start:0px] [margin-inline-end:0px]'>
					{title}
				</CardTitle>
				<CardDescription className='text-[#fff] text-center text-[16px] mb-7 font-[lexend] leading-[22px] opacity-80'>
					{description}
				</CardDescription>
			</CardHeader>
			<CardFooter className='flex justify-center pb-6 w-full mt-auto'>
				<Button
					className={`${buttonColors} text-white text-[16px] flex items-center justify-center text-center font-[lexend] font-semibold !rounded-xl w-full !h-auto mt-auto border-0 leading-4 !py-4 !px-10 !tracking-normal cursor-pointer min-h-[50px]`}
				>
					{buttonText}
				</Button>
			</CardFooter>

			{/* Subtle bottom decorative element */}
			<div className='absolute bottom-3 left-1/2 transform -translate-x-1/2 w-16 h-px bg-gradient-to-r from-transparent via-white/30 to-transparent'></div>
		</Card>
	);
}
