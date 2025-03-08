import ProducteFeature from './ProducteFeature';
import Quotes from './Quotes';
export default function OverviewSection() {
	return (
		<section className='bg-[#FFFCF5] flex flex-col justify-center items-center w-full'>
			<ProducteFeature />
			<Quotes />
		</section>
	);
}
