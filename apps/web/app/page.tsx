export default function Home() {
  return (
    <main style={{ fontFamily: 'system-ui, sans-serif', padding: '2rem' }}>
      <h1>Groceries</h1>
      <p>Find the most cost-effective way to shop your grocery list.</p>
      <p><a href="/admin/store-candidates">Store candidate approval queue</a></p>
      <p><a href="/admin/product-selection-reviews">Product selection review queue</a></p>
    </main>
  );
}
