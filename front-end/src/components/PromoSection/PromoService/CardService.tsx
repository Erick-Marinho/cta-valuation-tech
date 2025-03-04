import { Button } from '@/components/ui/button';
import {
	Card,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle,
} from '@/components/ui/card';

export function CardService({
	icon,
	title,
	description,
	buttonText,
}: {
	icon: React.ReactNode;
	title: string;
	description: string;
	buttonText: string;
}) {
	return (
		<Card className='flex flex-col w-[calc((100%-(16px*3))/4)]  rounded-xl backdrop-blur-[20px] pt-[60px] px-5 pb-[30px] shadow-[0_3px_5px_#0000001a] bg-[#121212] text-white text-center'>
			<CardHeader className='flex items-center'>
				<div className='bg-amber-50 h-12 w-12 rounded-full flex items-center justify-center'>
					{icon}
				</div>
				<CardTitle className='block text-2xl text-center font-[lexend] pb-[30px] font-normal text-[20px] leading-7 m-0 p-0 [margin-block-start:1em] [margin-block-end:1em] [margin-inline-start:0px] [margin-inline-end:0px]'>
					{title}
				</CardTitle>
				<CardDescription className='text-[#fff] text-center text-[16px] mb-7 font-[lexend] leading-[22px]'>
					{description}
				</CardDescription>
			</CardHeader>
			<CardFooter className='flex justify-center pb-6'>
				<Button className='bg-[#cf13a3] hover:bg-[#B71DAD] text-white text-[16px] text-center font-[lexend] font-semibold !rounded-xl w-full !h-auto mt-auto border-0 leading-4 !py-3 !px-8 !tracking-normal cursor-pointer'>
					{buttonText}
				</Button>
			</CardFooter>
		</Card>
	);
}
