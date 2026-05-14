import { Dialog, Transition } from "@headlessui/react";
import { Fragment } from "react";
import { Link } from "react-router-dom";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { useCart, useRemoveFromCart } from "../../hooks/useCart";
import { useAuthStore } from "../../store/authStore";
import { formatPrice } from "../../lib/format";

interface CartDrawerProps {
  open: boolean;
  onClose: () => void;
}

export function CartDrawer({ open, onClose }: CartDrawerProps) {
  const user = useAuthStore((s) => s.user);
  const { data: cart, isLoading } = useCart();
  const removeMutation = useRemoveFromCart();

  return (
    <Transition show={open} as={Fragment}>
      <Dialog onClose={onClose} className="relative z-50">
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-150"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/30" />
        </Transition.Child>

        <div className="fixed inset-0 flex justify-end">
          <Transition.Child
            as={Fragment}
            enter="transform transition ease-out duration-300"
            enterFrom="translate-x-full"
            enterTo="translate-x-0"
            leave="transform transition ease-in duration-200"
            leaveFrom="translate-x-0"
            leaveTo="translate-x-full"
          >
            <Dialog.Panel className="w-full max-w-md bg-white shadow-xl flex flex-col h-full">
              <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                <Dialog.Title className="text-lg font-semibold">
                  Your cart
                </Dialog.Title>
                <button
                  onClick={onClose}
                  className="p-1 rounded-lg hover:bg-gray-100"
                  aria-label="Close cart"
                >
                  <XMarkIcon className="w-5 h-5" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto px-6 py-4">
                {!user ? (
                  <div className="text-sm text-gray-500 text-center py-12">
                    <p className="mb-4">Sign in to view your cart.</p>
                    <Link
                      to="/login"
                      onClick={onClose}
                      className="inline-block bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-4 py-2 rounded-lg"
                    >
                      Sign in
                    </Link>
                  </div>
                ) : isLoading ? (
                  <div className="text-sm text-gray-400">Loading…</div>
                ) : !cart || cart.items.length === 0 ? (
                  <div className="text-sm text-gray-500 text-center py-12">
                    Your cart is empty.
                  </div>
                ) : (
                  <ul className="space-y-3">
                    {cart.items.map((item) => (
                      <li
                        key={item.product_id}
                        className="flex gap-3 pb-3 border-b border-gray-100 last:border-0"
                      >
                        <div className="flex-1">
                          <p className="text-sm font-medium line-clamp-2">
                            {item.title}
                          </p>
                          <p className="text-xs text-gray-500 mt-1">
                            Qty: {item.quantity}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-semibold">
                            {formatPrice(item.price)}
                          </p>
                          <button
                            onClick={() =>
                              removeMutation.mutate(item.product_id)
                            }
                            disabled={removeMutation.isPending}
                            className="text-xs text-red-600 hover:underline mt-1"
                          >
                            Remove
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {user && cart && cart.items.length > 0 && (
                <div className="border-t border-gray-200 px-6 py-4 space-y-3">
                  <div className="flex justify-between font-semibold">
                    <span>Subtotal</span>
                    <span>{formatPrice(cart.subtotal)}</span>
                  </div>
                  <Link
                    to="/cart"
                    onClick={onClose}
                    className="block bg-brand-600 hover:bg-brand-700 text-white text-center font-medium py-2.5 rounded-lg transition"
                  >
                    View full cart
                  </Link>
                </div>
              )}
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition>
  );
}
