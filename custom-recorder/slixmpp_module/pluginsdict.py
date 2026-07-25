# Slixmpp: The Slick XMPP Library
# Copyright © 2021 Mathieu Pasquet <mathieui@mathieui.net>
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.

from typing import TypedDict

# Plugins mega-dict
from slixmpp.features.feature_bind import FeatureBind
from slixmpp.features.feature_limits import FeatureLimits
from slixmpp.features.feature_mechanisms import FeatureMechanisms
from slixmpp.features.feature_preapproval import FeaturePreApproval
from slixmpp.features.feature_rosterver import FeatureRosterVer
from slixmpp.features.feature_session import FeatureSession
from slixmpp.features.feature_starttls import FeatureSTARTTLS
from slixmpp.plugins.xep_0004 import XEP_0004
from slixmpp.plugins.xep_0009 import XEP_0009
from slixmpp.plugins.xep_0012 import XEP_0012
from slixmpp.plugins.xep_0013 import XEP_0013
from slixmpp.plugins.xep_0016 import XEP_0016
from slixmpp.plugins.xep_0020 import XEP_0020
from slixmpp.plugins.xep_0027 import XEP_0027
from slixmpp.plugins.xep_0030 import XEP_0030
from slixmpp.plugins.xep_0033 import XEP_0033
from slixmpp.plugins.xep_0045 import XEP_0045
from slixmpp.plugins.xep_0047 import XEP_0047
from slixmpp.plugins.xep_0048 import XEP_0048
from slixmpp.plugins.xep_0049 import XEP_0049
from slixmpp.plugins.xep_0050 import XEP_0050
from slixmpp.plugins.xep_0054 import XEP_0054
from slixmpp.plugins.xep_0055 import XEP_0055
from slixmpp.plugins.xep_0059 import XEP_0059
from slixmpp.plugins.xep_0060 import XEP_0060
from slixmpp.plugins.xep_0065 import XEP_0065
from slixmpp.plugins.xep_0066 import XEP_0066
from slixmpp.plugins.xep_0070 import XEP_0070
from slixmpp.plugins.xep_0071 import XEP_0071
from slixmpp.plugins.xep_0077 import XEP_0077
from slixmpp.plugins.xep_0078 import XEP_0078
from slixmpp.plugins.xep_0079 import XEP_0079
from slixmpp.plugins.xep_0080 import XEP_0080
from slixmpp.plugins.xep_0082 import XEP_0082
from slixmpp.plugins.xep_0084 import XEP_0084
from slixmpp.plugins.xep_0085 import XEP_0085
from slixmpp.plugins.xep_0086 import XEP_0086
from slixmpp.plugins.xep_0091 import XEP_0091
from slixmpp.plugins.xep_0092 import XEP_0092
from slixmpp.plugins.xep_0095 import XEP_0095
from slixmpp.plugins.xep_0096 import XEP_0096
from slixmpp.plugins.xep_0100 import XEP_0100
from slixmpp.plugins.xep_0106 import XEP_0106
from slixmpp.plugins.xep_0107 import XEP_0107
from slixmpp.plugins.xep_0108 import XEP_0108
from slixmpp.plugins.xep_0115 import XEP_0115
from slixmpp.plugins.xep_0118 import XEP_0118
from slixmpp.plugins.xep_0122 import XEP_0122
from slixmpp.plugins.xep_0128 import XEP_0128
from slixmpp.plugins.xep_0131 import XEP_0131
from slixmpp.plugins.xep_0133 import XEP_0133
from slixmpp.plugins.xep_0152 import XEP_0152
from slixmpp.plugins.xep_0153 import XEP_0153
from slixmpp.plugins.xep_0163 import XEP_0163
from slixmpp.plugins.xep_0172 import XEP_0172
from slixmpp.plugins.xep_0184 import XEP_0184
from slixmpp.plugins.xep_0186 import XEP_0186
from slixmpp.plugins.xep_0191 import XEP_0191
from slixmpp.plugins.xep_0196 import XEP_0196
from slixmpp.plugins.xep_0198 import XEP_0198
from slixmpp.plugins.xep_0199 import XEP_0199
from slixmpp.plugins.xep_0202 import XEP_0202
from slixmpp.plugins.xep_0203 import XEP_0203
from slixmpp.plugins.xep_0221 import XEP_0221
from slixmpp.plugins.xep_0222 import XEP_0222
from slixmpp.plugins.xep_0223 import XEP_0223
from slixmpp.plugins.xep_0224 import XEP_0224
from slixmpp.plugins.xep_0231 import XEP_0231
from slixmpp.plugins.xep_0234 import XEP_0234
from slixmpp.plugins.xep_0235 import XEP_0235
from slixmpp.plugins.xep_0242 import XEP_0242
from slixmpp.plugins.xep_0249 import XEP_0249
from slixmpp.plugins.xep_0256 import XEP_0256
from slixmpp.plugins.xep_0257 import XEP_0257
from slixmpp.plugins.xep_0258 import XEP_0258
from slixmpp.plugins.xep_0264 import XEP_0264
from slixmpp.plugins.xep_0270 import XEP_0270
from slixmpp.plugins.xep_0279 import XEP_0279
from slixmpp.plugins.xep_0280 import XEP_0280
from slixmpp.plugins.xep_0292 import XEP_0292
from slixmpp.plugins.xep_0297 import XEP_0297
from slixmpp.plugins.xep_0300 import XEP_0300
from slixmpp.plugins.xep_0302 import XEP_0302
from slixmpp.plugins.xep_0308 import XEP_0308
from slixmpp.plugins.xep_0313 import XEP_0313
from slixmpp.plugins.xep_0317 import XEP_0317
from slixmpp.plugins.xep_0319 import XEP_0319
from slixmpp.plugins.xep_0323 import XEP_0323
from slixmpp.plugins.xep_0325 import XEP_0325
from slixmpp.plugins.xep_0332 import XEP_0332
from slixmpp.plugins.xep_0333 import XEP_0333
from slixmpp.plugins.xep_0334 import XEP_0334
from slixmpp.plugins.xep_0335 import XEP_0335
from slixmpp.plugins.xep_0352 import XEP_0352
from slixmpp.plugins.xep_0353 import XEP_0353
from slixmpp.plugins.xep_0356 import XEP_0356
from slixmpp.plugins.xep_0359 import XEP_0359
from slixmpp.plugins.xep_0363 import XEP_0363
from slixmpp.plugins.xep_0369 import XEP_0369
from slixmpp.plugins.xep_0372 import XEP_0372
from slixmpp.plugins.xep_0377 import XEP_0377
from slixmpp.plugins.xep_0380 import XEP_0380
from slixmpp.plugins.xep_0382 import XEP_0382
from slixmpp.plugins.xep_0385 import XEP_0385
from slixmpp.plugins.xep_0394 import XEP_0394
from slixmpp.plugins.xep_0402 import XEP_0402
from slixmpp.plugins.xep_0403 import XEP_0403
from slixmpp.plugins.xep_0404 import XEP_0404
from slixmpp.plugins.xep_0405 import XEP_0405
from slixmpp.plugins.xep_0410 import XEP_0410
from slixmpp.plugins.xep_0421 import XEP_0421
from slixmpp.plugins.xep_0422 import XEP_0422
from slixmpp.plugins.xep_0424 import XEP_0424
from slixmpp.plugins.xep_0425 import XEP_0425
from slixmpp.plugins.xep_0428 import XEP_0428
from slixmpp.plugins.xep_0437 import XEP_0437
from slixmpp.plugins.xep_0439 import XEP_0439
from slixmpp.plugins.xep_0441 import XEP_0441
from slixmpp.plugins.xep_0444 import XEP_0444
from slixmpp.plugins.xep_0446 import XEP_0446
from slixmpp.plugins.xep_0447 import XEP_0447
from slixmpp.plugins.xep_0449 import XEP_0449
from slixmpp.plugins.xep_0454 import XEP_0454
from slixmpp.plugins.xep_0455 import XEP_0455
from slixmpp.plugins.xep_0461 import XEP_0461
from slixmpp.plugins.xep_0462 import XEP_0462
from slixmpp.plugins.xep_0463 import XEP_0463
from slixmpp.plugins.xep_0469 import XEP_0469
from slixmpp.plugins.xep_0482 import XEP_0482
from slixmpp.plugins.xep_0490 import XEP_0490
from slixmpp.plugins.xep_0492 import XEP_0492
from slixmpp.plugins.xep_0494 import XEP_0494
from slixmpp.plugins.xep_0502 import XEP_0502
from slixmpp.plugins.xep_0511 import XEP_0511
from slixmpp.plugins.xep_0513 import XEP_0513


class PluginsDict(TypedDict):
    feature_bind: FeatureBind
    feature_limits: FeatureLimits
    feature_mechanisms: FeatureMechanisms
    feature_preapproval: FeaturePreApproval
    feature_rosterver: FeatureRosterVer
    feature_session: FeatureSession
    feature_starttls: FeatureSTARTTLS
    xep_0004: XEP_0004
    xep_0009: XEP_0009
    xep_0012: XEP_0012
    xep_0013: XEP_0013
    xep_0016: XEP_0016
    xep_0020: XEP_0020
    xep_0027: XEP_0027
    xep_0030: XEP_0030
    xep_0033: XEP_0033
    xep_0045: XEP_0045
    xep_0047: XEP_0047
    xep_0048: XEP_0048
    xep_0049: XEP_0049
    xep_0050: XEP_0050
    xep_0054: XEP_0054
    xep_0055: XEP_0055
    xep_0059: XEP_0059
    xep_0060: XEP_0060
    xep_0065: XEP_0065
    xep_0066: XEP_0066
    xep_0070: XEP_0070
    xep_0071: XEP_0071
    xep_0077: XEP_0077
    xep_0078: XEP_0078
    xep_0079: XEP_0079
    xep_0080: XEP_0080
    xep_0082: XEP_0082
    xep_0084: XEP_0084
    xep_0085: XEP_0085
    xep_0086: XEP_0086
    xep_0091: XEP_0091
    xep_0092: XEP_0092
    xep_0095: XEP_0095
    xep_0096: XEP_0096
    xep_0100: XEP_0100
    xep_0106: XEP_0106
    xep_0107: XEP_0107
    xep_0108: XEP_0108
    xep_0115: XEP_0115
    xep_0118: XEP_0118
    xep_0122: XEP_0122
    xep_0128: XEP_0128
    xep_0131: XEP_0131
    xep_0133: XEP_0133
    xep_0152: XEP_0152
    xep_0153: XEP_0153
    xep_0163: XEP_0163
    xep_0172: XEP_0172
    xep_0184: XEP_0184
    xep_0186: XEP_0186
    xep_0191: XEP_0191
    xep_0196: XEP_0196
    xep_0198: XEP_0198
    xep_0199: XEP_0199
    xep_0202: XEP_0202
    xep_0203: XEP_0203
    xep_0221: XEP_0221
    xep_0222: XEP_0222
    xep_0223: XEP_0223
    xep_0224: XEP_0224
    xep_0231: XEP_0231
    xep_0234: XEP_0234
    xep_0235: XEP_0235
    xep_0242: XEP_0242
    xep_0249: XEP_0249
    xep_0256: XEP_0256
    xep_0257: XEP_0257
    xep_0258: XEP_0258
    xep_0264: XEP_0264
    xep_0270: XEP_0270
    xep_0279: XEP_0279
    xep_0280: XEP_0280
    xep_0292: XEP_0292
    xep_0297: XEP_0297
    xep_0300: XEP_0300
    xep_0302: XEP_0302
    xep_0308: XEP_0308
    xep_0313: XEP_0313
    xep_0317: XEP_0317
    xep_0319: XEP_0319
    xep_0323: XEP_0323
    xep_0325: XEP_0325
    xep_0332: XEP_0332
    xep_0333: XEP_0333
    xep_0334: XEP_0334
    xep_0335: XEP_0335
    xep_0352: XEP_0352
    xep_0353: XEP_0353
    xep_0356: XEP_0356
    xep_0359: XEP_0359
    xep_0363: XEP_0363
    xep_0369: XEP_0369
    xep_0372: XEP_0372
    xep_0377: XEP_0377
    xep_0380: XEP_0380
    xep_0382: XEP_0382
    xep_0385: XEP_0385
    xep_0394: XEP_0394
    xep_0402: XEP_0402
    xep_0403: XEP_0403
    xep_0404: XEP_0404
    xep_0405: XEP_0405
    xep_0410: XEP_0410
    xep_0421: XEP_0421
    xep_0422: XEP_0422
    xep_0424: XEP_0424
    xep_0425: XEP_0425
    xep_0428: XEP_0428
    xep_0437: XEP_0437
    xep_0439: XEP_0439
    xep_0441: XEP_0441
    xep_0444: XEP_0444
    xep_0446: XEP_0446
    xep_0447: XEP_0447
    xep_0449: XEP_0449
    xep_0454: XEP_0454
    xep_0455: XEP_0455
    xep_0461: XEP_0461
    xep_0462: XEP_0462
    xep_0463: XEP_0463
    xep_0469: XEP_0469
    xep_0482: XEP_0482
    xep_0490: XEP_0490
    xep_0492: XEP_0492
    xep_0494: XEP_0494
    xep_0502: XEP_0502
    xep_0511: XEP_0511
    xep_0513: XEP_0513
