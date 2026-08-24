"""pytest'in TUM test modullerinden once calistirdigi kok conftest.

TEK AMACI: .env dosyasini process ortamina yuklemek (bkz. ortam_yukle.py).
pytest, bir dizindeki testleri toplamadan once o dizinin conftest.py'sini
import eder - bu, testler chunking.embedding/evren_istemci gibi ortam
degiskenini IMPORT ANINDA okuyan modulleri import etmeden once .env'in
zaten yuklenmis olmasini garanti eder.
"""

import ortam_yukle  # noqa: F401 - side effect: .env process ortamina yuklenir
