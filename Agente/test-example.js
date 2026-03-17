// Test file for Restricted Copilot Extension
// This file demonstrates the extension's functionality

function calculateTotal(items, taxRate) {
    let total = 0;
    
    // TODO: Add validation for negative values
    for (let i = 0; i < items.length; i++) {
        total += items[i].price * items[i].quantity;
    }
    
    // Calculate tax
    const tax = total * taxRate;
    
    console.log("Debug: total before tax:", total);
    
    return total + tax;
}

function processOrder(order) {
    // FIXME: This function needs error handling
    if (!order) {
        return null;
    }
    
    const total = calculateTotal(order.items, 0.08);
    
    return {
        orderId: order.id,
        total: total,
        status: 'processed'
    };
}

class OrderManager {
    constructor() {
        this.orders = [];
    }
    
    addOrder(order) {
        this.orders.push(order);
        return this.processOrder(order);
    }
    
    processOrder(order) {
        // This method has some issues that the extension should detect
        return processOrder(order);
    }
}
