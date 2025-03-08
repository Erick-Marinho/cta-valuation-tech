import LogoCards from './Logo-Cards';
import VideoContainer from './VideoContainer';

export default function VideoPromo() {
	return (
		<section className='block bg-[#222228] text-[#fff] pt-[120px] pb-[120px] pr-0'>
			<VideoContainer />
			<LogoCards />
		</section>
	);
}
