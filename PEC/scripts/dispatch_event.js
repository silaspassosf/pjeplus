// Dispara evento customizado em um elemento
// Uso: arguments[0] = elemento, arguments[1] = nome do evento
var evt = new Event(arguments[1], {bubbles:true});
arguments[0].dispatchEvent(evt);