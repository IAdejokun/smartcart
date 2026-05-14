import { Link } from "react-router-dom";
import { useCart, useRemoveFromCart } from "../hooks/useCart";
import { formatPrice } from "../lib/format";

export default function CartPage() {
  const { data: cart, isLoading } = useCart();
  const removeMutation = useRemoveFromCart();

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-white rounded-2xl border border-gray-200 h-64 animate-pulse" />
      </div>
    );
  }

  if (!cart || cart.items.length === 0) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12 text-center">
        <h1 className="text-2xl font-semibold mb-2">Your cart is empty</h1>
        <p className="text-gray-500 mb-6">
          Browse the storefront to find something you'll like.
        </p>
        <Link
          to="/"
          className="inline-block bg-brand-600 hover:bg-brand-700 text-white font-medium px-5 py-2.5 rounded-lg"
        >
          Continue shopping
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-semibold mb-6">Your cart</h1>

      <div className="bg-white rounded-2xl border border-gray-200 divide-y divide-gray-100">
        {cart.items.map((item) => (
          <div
            key={item.product_id}
            className="px-6 py-4 flex items-center gap-4"
          >
            <div className="flex-1">
              <Link
                to={`/products/${item.product_id}`}
                className="font-medium hover:text-brand-600"
              >
                {item.title}
              </Link>
              <p className="text-sm text-gray-500 mt-0.5">
                Quantity: {item.quantity}
              </p>
            </div>
            <div className="text-right">
              <p className="font-semibold">{formatPrice(item.price)}</p>
              <button
                onClick={() => removeMutation.mutate(item.product_id)}
                disabled={removeMutation.isPending}
                className="text-xs text-red-600 hover:underline mt-1"
              >
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 mt-4 p-6">
        <div className="flex items-center justify-between text-lg font-semibold mb-1">
          <span>Subtotal</span>
          <span>{formatPrice(cart.subtotal)}</span>
        </div>
        <p className="text-xs text-gray-500 mb-4">{cart.item_count} items</p>
        <button
          disabled
          className="w-full bg-gray-300 text-gray-500 font-medium py-2.5 rounded-lg cursor-not-allowed"
          title="Checkout flow is out of MVP scope"
        >
          Checkout (demo only)
        </button>
      </div>
    </div>
  );
}
