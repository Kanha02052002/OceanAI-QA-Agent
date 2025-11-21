# Product Specifications & Business Rules

## Available Products

### Laptop
- Price: $999
- Category: Electronics

### Headphones
- Price: $199
- Category: Audio

### Mouse
- Price: $49
- Category: Accessories

---

## Discount Rules

- The system supports **one discount code**:  
  **SAVE10 → applies a 10% discount** on the product subtotal.
  
- Discount code is applied only once per checkout session.  
- Discount applies **only to product total**, not shipping.  
- Invalid codes must display a red error message:  
  `"Invalid discount code."`

- When the discount is already applied, show:  
  `"Discount already applied."` in gray text.

- After applying a valid coupon, the UI must show:  
  `"10% discount applied!"` in green.

---

## Shipping Rules

- **Standard Shipping**  
  - Cost: $0 (Free)  
  - Radio button name: `shipping`  
  - Value: `"standard"`

- **Express Shipping**  
  - Cost: $10  
  - Value: `"express"`

---

## Payment Method Rules

- Payment method is required for checkout.  
- Available options (value attributes):  
  - `card` (Credit Card)  
  - `paypal` (PayPal)  
  - `bank` (Bank Transfer)

---

## Cart & Order Rules

- Cart total is calculated as:  
  **Total = Sum of product prices − Discount + Shipping**

- Discount is *not* cumulative and can only be applied once.  
- Cart cannot be empty when placing an order.  
- Pressing **"Pay Now"** triggers form validation and payment confirmation.  
