import LogoCards from './Logo-Cards';
import VideoContainer from './VideoContainer';

export default function VideoPromo() {
	return (
		<section className='bg-[#222228] flex flex-col justify-center items-center py-16 md:py-24'>
			<VideoContainer />
			<LogoCards />
		</section>
	);
}
