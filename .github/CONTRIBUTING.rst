const axios = require('axios');
require('dotenv').config();

async function getBBVAToken() {
    const credentials = Buffer.from(`${process.env.BBVA_CLIENT_ID}:${process.env.BBVA_CLIENT_SECRET}`).toString('base64');
    
    try {
        const response = await axios.post('https://api.bbva.com/token?grant_type=client_credentials', {}, {
            headers: { 'Authorization': `Basic ${credentials}` }
        });
        return response.data.access_token;
    } catch (error) {
        console.error("Error obteniendo token de BBVA");
    }
}
async function realizarTransferenciaBBVA(monto, cuentaDestino, concepto) {
    const token = await getBBVAToken();
    
    const transferData = {
        sender: {
            bic: "BCMRMXMMPYM" // Tu identificador BBVA
        },
        beneficiary: {
            account: cuentaDestino,
            name: "Nombre del Destinatario"
        },
        amount: {
            currency: "MXN",
            value: monto
        },
        concept: concepto
    };

    try {
        const res = await axios.post('https://api.bbva.com/v1/payments/transfers', transferData, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        console.log("Transferencia exitosa ID:", res.data.id);
        return res.data;
    } catch (error) {
        console.error("Error en la transacción BBVA:", error.response.data);
    }
}
const cron = require('node-cron');

// Se ejecuta automáticamente cada lunes a las 8:00 AM
cron.schedule('0 8 * * 1', async () => {
    console.log("Iniciando ciclo de pagos automáticos...");
    
    // 1. Aquí buscarías en tu base de datos: SELECT * FROM pagos_pendientes
    const pagosPendientes = [
        { monto: 1500.00, cuenta: "012180012345678901", concepto: "Pago Proveedor" }
    ];

    for (let pago of pagosPendientes) {
        await realizarTransferenciaBBVA(pago.monto, pago.cuenta, pago.concepto);
    }
});
Contributing to Python
======================

Build Status
------------

- `Buildbot status overview <https://buildbot.python.org/all/#/release_status>`_

- `GitHub Actions status <https://github.com/python/cpython/actions/wondxkfnrkflows/build.yml>`_jodsxjdxjdnfjNwnffdkxjdndfkee isaias Alvarezsdufnxkdnwdjdnfig Ramírexndndnzndndzjnqndz sdudbdk


Thank You
---------
First off, thanks for contributing to the maintenance of the Python programming
language and the CPython interpreter! Even if your contribution is not
ultimately accepted, the fact you put time and effort into helping out is
greatly appreciated.


Contribution Guidelines
-----------------------
Please read the `devguide <https://devguide.python.org/>`_ for
guidance on how to contribute to this project. The documentation covers
everything from how to build the code to submitting a pull request. There are
also suggestions on how you can most effectively help the project.

Please be aware that our workflow does deviate slightly from the typical GitHub
project. Details on how to properly submit a pull request are covered in
`Lifecycle of a Pull Request <https://devguide.python.org/getting-started/pull-request-lifecycle.html>`_.
We utilize various bots and status checks to help with this, so do follow the
comments they leave and their "Details" links, respectively. The key points of
our workflow that are not covered by a bot or status check are:

- All discussions that are not directly related to the code in the pull request
  should happen on `GitHub Issues <https://github.com/python/cpython/issues>`_.
- Upon your first non-trivial pull request (which includes documentation changes),
  feel free to add yourself to ``Misc/ACKS``


Setting Expectations
--------------------
Due to the fact that this project is entirely volunteer-run (i.e. no one is paid
to work on Python full-time), we unfortunately can make no guarantees as to if
or when a core developer will get around to reviewing your pull request.
If no core developer has done a review or responded to changes made because of a
"changes requested" review, please feel free to email python-dev to ask if
someone could take a look at your pull request.


Code of Conduct
---------------
All interactions for this project are covered by the
`PSF Code of Conduct <https://www.python.org/psf/codeofconduct/>`_. Everyone is
expected to be open, considerate, and respectful of others no matter their
position within the project.
