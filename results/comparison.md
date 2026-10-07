# RAG-EAM frente a LLM directo

> **Reporte parcial:** faltan 28 de 100 preguntas.

Modelo generador: `gpt-5.5` · juez: `gpt-5.5` · recuperación: 5 obras / 8 fragmentos · 72 preguntas (72 sobre el corpus, 0 fuera del corpus).

Exactitud = correcto + 0.5·parcial.

## Preguntas sobre el corpus (72)

| Sistema | n | Exactitud | Correcto | Parcial | Incorrecto | No lo sé |
|---|---|---|---|---|---|---|
| RAG-EAM | 72 | **0.42** | 42% | 1% | 1% | 56% |
| LLM directo | 72 | **0.63** | 58% | 10% | 18% | 14% |

### Obras conocidas (48)

| Sistema | n | Exactitud | Correcto | Parcial | Incorrecto | No lo sé |
|---|---|---|---|---|---|---|
| RAG-EAM | 48 | **0.45** | 44% | 2% | 2% | 52% |
| LLM directo | 48 | **0.84** | 79% | 10% | 8% | 2% |

### Obras poco conocidas (24)

| Sistema | n | Exactitud | Correcto | Parcial | Incorrecto | No lo sé |
|---|---|---|---|---|---|---|
| RAG-EAM | 24 | **0.38** | 38% | 0% | 0% | 62% |
| LLM directo | 24 | **0.21** | 17% | 8% | 38% | 38% |

### Según la recuperación de la EAM

La obra correcta está entre las recuperadas en 51/72 preguntas (71%); la evidencia literal llega al prompt en 23/72.


Con la obra recuperada (51):

| Sistema | n | Exactitud | Correcto | Parcial | Incorrecto | No lo sé |
|---|---|---|---|---|---|---|
| RAG-EAM | 51 | **0.60** | 59% | 2% | 2% | 37% |
| LLM directo | 51 | **0.61** | 57% | 8% | 18% | 18% |

Sin la obra recuperada (21):

| Sistema | n | Exactitud | Correcto | Parcial | Incorrecto | No lo sé |
|---|---|---|---|---|---|---|
| RAG-EAM | 21 | **0.00** | 0% | 0% | 0% | 100% |
| LLM directo | 21 | **0.69** | 62% | 14% | 19% | 5% |

### Pregunta por pregunta (sólo "correcto")

- Ambos correctos: 17
- Sólo RAG correcto: 13
- Sólo LLM directo correcto: 25
- Ninguno: 17
- McNemar exacta (pares discordantes 13 vs 25): p = 0.073

## Costo en tokens (generación, sin el juez)

| Sistema | Tokens de entrada | Tokens de salida |
|---|---|---|
| RAG-EAM | 110,766 | 8,310 |
| LLM directo | 6,700 | 163,986 |

## Detalle

| # | Pregunta | Obra | Fama | EAM obra | RAG | Directo |
|---|---|---|---|---|---|---|
| 1 | ¿Qué enfermedad sufre Dahlmann tras golpearse la frente? | El sur | conocida | ✓ | correcto | correcto |
| 2 | ¿Qué ve el narrador en el sótano de la casa de la calle Garay? | El Aleph | conocida | ✗ | no_sabe | correcto |
| 3 | ¿Qué hacen los hermanos cuando los ruidos toman la parte del fondo de la casa? | Casa tomada | conocida | ✗ | no_sabe | correcto |
| 4 | ¿En qué animal se convierte el hombre que visita el acuario del Jardin des Plantes? | Axolotl | conocida | ✗ | no_sabe | correcto |
| 5 | ¿Qué novela lee el hombre sentado en el sillón de terciopelo verde? | Continuidad de los parques | conocida | ✓ | no_sabe | correcto |
| 6 | ¿Qué sueña el motociclista accidentado mientras está en el hospital? | La noche boca arriba | conocida | ✓ | no_sabe | correcto |
| 7 | ¿Qué vomita el narrador que se queda en el departamento de Andrée en Buenos Aires? | Carta a una señorita en París | conocida | ✓ | correcto | correcto |
| 8 | ¿Qué pasa con los automovilistas atrapados durante días en el embotellamiento de la autopista? | La autopista del sur | conocida | ✗ | no_sabe | correcto |
| 9 | ¿Cómo intenta fray Bartolomé Arrazola salvarse de los indígenas que lo iban a sacrificar? | El eclipse | conocida | ✓ | correcto | correcto |
| 10 | ¿Qué negocio hacía Mr. Taylor con las cabezas reducidas? | Míster Taylor | conocida | ✓ | correcto | correcto |
| 11 | ¿Qué hicieron con la oveja negra después de fusilarla? | La oveja negra | conocida | ✗ | no_sabe | correcto |
| 12 | ¿Qué le pide Juvencio Nava a su hijo que diga a quienes lo van a fusilar? | ¡Diles que no me maten! | conocida | ✓ | no_sabe | correcto |
| 13 | ¿A quién carga el padre sobre los hombros mientras camina de noche buscando Tonaya? | No oyes ladrar a los perros | conocida | ✗ | no_sabe | correcto |
| 14 | ¿Cómo es el viento y la tierra del pueblo de Luvina? | Luvina | conocida | ✓ | correcto | parcial |
| 15 | ¿Qué le pasó a la vaca de Tacha cuando creció el río? | Es que somos muy pobres | conocida | ✓ | correcto | correcto |
| 16 | ¿Qué le explica el guardagujas al forastero sobre los trenes y las estaciones? | El guardagujas | conocida | ✓ | parcial | parcial |
| 17 | ¿Qué encontró la hormiga que llevó al hormiguero un miligramo prodigioso? | El prodigioso miligramo | conocida | ✓ | incorrecto | incorrecto |
| 18 | ¿En qué cuento la vida de don Marcial transcurre al revés, de la muerte al nacimiento? | Viaje a la semilla | conocida | ✓ | correcto | correcto |
| 19 | ¿Con quién se encuentra Laura cuando su coche se detiene en el puente de Cuitzeo? | La culpa es de los tlaxcaltecas | conocida | ✗ | no_sabe | correcto |
| 20 | ¿Qué libro le presta al fin la hija del dueño de la librería a la narradora? | Felicidad clandestina | conocida | ✗ | no_sabe | correcto |
| 21 | ¿Qué hace la gallina que la salva de ser cocinada para el almuerzo? | Una gallina | conocida | ✓ | no_sabe | correcto |
| 22 | ¿En qué localidad venden los hermanos Nilsen a Juliana Burgos, y a quién? | La intrusa | conocida | ✓ | correcto | correcto |
| 23 | ¿Cómo se llama el barco nórdico en cuyos marineros busca Emma Zunz a un hombre en el puerto, y de dónde es? | Emma Zunz | conocida | ✓ | no_sabe | correcto |
| 24 | Según el minotauro que narra su propia vida, ¿cada cuánto tiempo y cuántos hombres entran en su casa? | La casa de Asterión | conocida | ✗ | no_sabe | correcto |
| 25 | En el sistema de numeración inventado por Ireneo Funes, ¿qué nombre usaba en lugar del número siete mil trece? | Funes el memorioso | conocida | ✓ | correcto | correcto |
| 26 | ¿Cuánto dinero escondió Baltasar Espinosa en uno de sus libros, por desconfianza hacia los Gutres, en la estancia Los Álamos? | El evangelio según Marcos | conocida | ✓ | correcto | incorrecto |
| 27 | ¿Por qué viaja tanto en avión el anciano escritor al que investiga el narrador por encargo de un diputado que sospechaba de un tráfico de órganos de viejos? | El caso de los viejitos voladores | poco_conocida | ✓ | no_sabe | no_sabe |
| 28 | ¿Con qué le llena Hebe los bolsillos a su marido Pedro para que su cuerpo, que ha perdido peso, no se eleve? | El leve Pedro | conocida | ✓ | correcto | parcial |
| 29 | En el hotel donde un huevo frito pasa de mano en mano entre varios cocineros y resulta delicioso, ¿qué regla culinaria establece el jefe de fiscalización? | Tres cocineros y un huevo frito | poco_conocida | ✗ | no_sabe | parcial |
| 30 | En el monólogo escrito en habla porteña sobre una pelea de boxeo en el Luna Park, ¿en qué asalto gana Bonavena al brasileño Pires y de qué modo? | El rulo | poco_conocida | ✗ | no_sabe | parcial |
| 31 | ¿Dónde muere el atorrante de la calle Corrientes, antiguo condiscípulo del narrador en el colegio del Salvador, y en qué noche? | Telesforo Altamira | poco_conocida | ✗ | no_sabe | incorrecto |
| 32 | ¿Cuántos ejemplares llevaba vendidos la primera edición de la novela cuyos gerundios suprimía el narrador antes de arrastrarse bajo el escritorio de su compañera del walkman? | El corrector | poco_conocida | ✓ | correcto | no_sabe |
| 33 | ¿Dónde termina encerrado Octaviano Crivellini, el copista de estatuas acosado por el niño Tirso en la pensión de Mme. Renard? | El vendedor de estatuas | poco_conocida | ✓ | no_sabe | incorrecto |
| 34 | En el armario de nogal cuyas habitantes se volvieron escritoras por la inacción y el aburrimiento, ¿cómo se titula la novela que escribió la novelista con gafas tras diez años de trabajo? | Las muñecas | poco_conocida | ✓ | correcto | incorrecto |
| 35 | El narrador vive toda una vida (boda en Ramos Mejía, mellizos en Liniers) durante un solo viaje por el Ferrocarril Oeste. ¿En qué estación se entera de la muerte de su esposa? | El tren | poco_conocida | ✗ | no_sabe | correcto |
| 36 | ¿Cómo mata la tía Pepa Mondelli a su gato negro después de que este devoró uno de sus pollitos? | El gato cocido | poco_conocida | ✓ | correcto | incorrecto |
| 37 | ¿Qué nombre lleva pintado el bote rojo que Chino Pérez trae a remolque a la isleta donde caza nutrias con Renato? | Los nutrieros | poco_conocida | ✓ | no_sabe | no_sabe |
| 38 | Tras quince días de inundación en la Buenos Aires rosista durante la cuaresma, ¿cuántos novillos llegan por el paso de Burgos para el abasto? | El matadero | conocida | ✓ | correcto | correcto |
| 39 | ¿Qué edad tiene la niña del matrimonio que vive en una casita de madera junto a tres líneas férreas, al pie de una montaña empinada, y de la que sus padres saben que algún día la matará un tren? | La hija del guardaagujas | poco_conocida | ✓ | no_sabe | correcto |
| 40 | ¿Qué descuento le recomienda el padrino moribundo a su ahijado para vender los muñecos de sacerdote y religiosas que difícilmente se venden en la tienda? | La tienda de muñecos | conocida | ✓ | no_sabe | no_sabe |
| 41 | ¿Qué le grita el loro Jesusito a Andrés Erre en el momento en que este se ahorca de una viga, tras descubrir la traición de su alter ego? | El difunto y yo | poco_conocida | ✓ | correcto | no_sabe |
| 42 | ¿Dónde va a caer el gnomo de cuero irlandés que vive sobre la balanza de cartas del escritorio de un poeta cuando, furioso, intenta echar a los dos menestriles que fueron sus compañeros? | El genio del pesacartas | poco_conocida | ✓ | correcto | correcto |
| 43 | ¿Qué piden en la confitería el hombre de la quemadura junto a la boca y la mujer del pómulo hundido después de conocerse en la cola del cine? | La noche de los feos | conocida | ✗ | no_sabe | parcial |
| 44 | Al final, ¿en qué pocillo pide tomar el café José Claudio, el marido ciego de Mariana, cuando ella se lo iba a servir en el verde? | Los pocillos | conocida | ✓ | correcto | incorrecto |
| 45 | ¿Cuánto tiempo llevaba el viejito jorobado del cartapacio acudiendo cada día a pedir audiencia con el Señor X, Director General de la Confederación Internacional de la Producción Universal? | El acto libre | poco_conocida | ✗ | no_sabe | no_sabe |
| 46 | ¿Qué hace que Carlos y Ramón guarden las armas cuando están a punto de batirse a muerte por la herencia de su hermana Luisana? | El piano viejo | poco_conocida | ✓ | no_sabe | no_sabe |
| 47 | ¿Qué decía el cartel de la tienda tranquila y limpia que sedujo al narrador de niño cuando acompañó a su madre a buscar unos cubiertos robados a una casa de empeños? | China | poco_conocida | ✗ | no_sabe | incorrecto |
| 48 | ¿Cómo se llama la isla griega que el steward Marini contempla por la ventanilla en sus vuelos de la línea Roma-Teherán? | La isla a mediodía | conocida | ✓ | correcto | correcto |
| 49 | ¿Qué firma llevaba el primer papelito, atado a una tuerca, que cayó del tren frente a Leticia, Holanda y la narradora mientras jugaban a las estatuas junto a las vías? | Final del juego | conocida | ✓ | correcto | correcto |
| 50 | ¿En qué ciudad y en qué lugar se encuentra Alina Reyes con la mujer harapienta con la que se abraza durante su viaje de bodas? | Lejana | conocida | ✗ | no_sabe | correcto |
| 51 | ¿Por qué rompe a llorar la viuda de los ojos ahumados cuando el narrador empieza a probar el piano en la reunión donde había leído un cuento? | Nadie encendía las lámparas | poco_conocida | ✓ | no_sabe | correcto |
| 52 | ¿Qué marca de medias vendía el concertista de piano convertido en corredor comercial que se ponía a llorar en las tiendas para vender más? | El cocodrilo | poco_conocida | ✓ | no_sabe | incorrecto |
| 53 | ¿Por qué derribaron el gomero que estaba pegado a la ventana del cuarto de vestir de Brígida, la joven esposa de Luis? | El árbol | conocida | ✓ | no_sabe | correcto |
| 54 | ¿Cómo se asegura el viejo minero de que su hijo Pablo, de ocho años, no abandone la puerta de ventilación que debe manejar en el fondo de la mina? | La compuerta número 12 | conocida | ✓ | no_sabe | correcto |
| 55 | ¿Qué hace María de los Ángeles después de ver subir del pozo el cadáver de su hijo, el joven minero apodado Cabeza de Cobre, muerto en un derrumbe? | El Chiflón del Diablo | conocida | ✓ | no_sabe | correcto |
| 56 | ¿Qué le pasó a la vela que Natalia puso entre las manos de Tanilo Santos cuando él rezaba arrodillado frente a la Virgen? | Talpa | conocida | ✓ | correcto | correcto |
| 57 | ¿Qué le manda hacer su madrina al muchacho siempre hambriento, al que Felipa da de comer, mientras está sentado junto a la alcantarilla? | Macario | conocida | ✓ | no_sabe | correcto |
| 58 | ¿Dónde vio por primera vez el narrador la araña venenosa que después soltó en su departamento, y con quién estaba? | La migala | conocida | ✗ | no_sabe | correcto |
| 59 | En el anuncio de Arreola sobre el aparato que convierte en electricidad los movimientos de los niños, ¿qué casa fabricante lo garantiza y dónde está? | Baby H. P. | conocida | ✗ | no_sabe | incorrecto |
| 60 | ¿Cómo presenta el profesor Fombona al joven poeta Feijoo ante Marcel Bataillon? | Obras completas | poco_conocida | ✓ | correcto | incorrecto |
| 61 | ¿Qué palabras estaban grabadas en la alianza que apareció cosida a la camisa de Adrián Cadena, a la altura del corazón? | El anillo | poco_conocida | ✓ | correcto | no_sabe |
| 62 | ¿Cómo acaban la narradora y Guadalupe con el ser de ojos amarillos que el marido llevó a vivir a la casa? | El huésped | conocida | ✓ | no_sabe | correcto |
| 63 | Según le cuentan doña Magdalena y Amalia a Alfonso, ¿cómo perdió la vista el capitán de Artillería? | La cena | poco_conocida | ✗ | no_sabe | incorrecto |
| 64 | En su texto irónico sobre los inconvenientes de ser ejecutado ante un pelotón, ¿a qué atribuye Julio Torri la palidez de muchos condenados en el postrer trance? | De fusilamientos | poco_conocida | ✓ | no_sabe | incorrecto |
| 65 | ¿Qué revela Sacramento después de que la asamblea de ejidatarios e ingenieros aprueba que los de San Juan de las Manzanas castiguen a su Presidente Municipal? | La muerte tiene permiso | conocida | ✓ | correcto | correcto |
| 66 | Después de que el granizo destruye su cosecha, Lencho pide cien pesos por correo; ¿cuánto dinero le llega y a quién culpa del faltante? | Una carta a Dios | conocida | ✓ | correcto | parcial |
| 67 | ¿Cómo muere el Conde Fabricio de Portinaris al huir aterrado de la aparición del Cardenal? | La puerta de bronce | poco_conocida | ✓ | correcto | no_sabe |
| 68 | ¿Qué pasa con el pliego que don Alejandro encuentra dentro del sobre del cofre de hierro? | El cofre | poco_conocida | ✓ | correcto | no_sabe |
| 69 | ¿Cómo consigue la hiena del zoológico un rostro para ir al baile en lugar de la joven narradora? | La debutante | conocida | ✗ | no_sabe | correcto |
| 70 | ¿Qué estaba haciendo el ciego que Ana ve desde el tranvía y que desencadena su crisis? | Amor | conocida | ✓ | correcto | correcto |
| 71 | ¿Qué trabajo le impone el rey al poeta hambriento que llega a su corte para que se gane la comida? | El rey burgués | conocida | ✓ | correcto | correcto |
| 72 | ¿Cómo se llama el cerdo que don Santos, el abuelo de pierna de palo, engorda con la basura que recogen sus nietos Efraín y Enrique? | Los gallinazos sin plumas | conocida | ✓ | correcto | correcto |
