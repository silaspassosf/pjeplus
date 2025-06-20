// ...existing code...

// Replace this:
// await page.click('.pec-polo-passivo-partes-processo');
// or something similar with:
await page.click('.fa.fa-user.pec-polo-passivo-partes-processo.pec-botao-intimar-polo-partes-processo');

// Replace something like:
// const element = await page.$('.pec-polo-passivo-partes-processo');
// await element.click();
// With:
const element = await page.$('.fa.fa-user.pec-polo-passivo-partes-processo.pec-botao-intimar-polo-partes-processo');
await element.click();

// ...existing code...