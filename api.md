openapi: 3.0.3
info:
  title: GigaChat API
  version: 1.0.0
  contact:
    name: GigaChat API
    url: 'https://developers.sber.ru/portal/products/gigachat-api'
    email: gigachat@sberbank.ru
  description: |
  
    Справочная документация по REST API нейросетевой модели GigaChat.

    О стоимости и условиях использования GigaChat API вы можете узнать в разделе [Тарифы и оплата](/ru/gigachat/api/tariffs).

    ## Получение токена доступа и авторизация запросов

    Запросы к GigaChat API передаются по адресу `https://gigachat.devices.sberbank.ru/` и авторизуются с помощью токена доступа по протоколу [OAuth 2.0](https://tools.ietf.org/html/rfc6749).
    Токен доступа передается в заголовке `Authorization`:
    
    ```sh
    curl -L -X GET 'https://gigachat.devices.sberbank.ru/api/v1/models' \
    -H 'Accept: application/json' \
    -H 'Authorization: Bearer <токен_доступа>'
    ```

    :::tip
    
    Вы также можете передавать запросы к [моделям в раннем доступе](/ru/gigachat/models/preview-models).
    Их возможности могут отличаться от моделей, доступных в промышленном контуре.    
    :::

    Чтобы получить токен, отправьте запрос [POST /api/v2/oauth](/ru/gigachat/api/reference/rest/post-token):

    ```sh
    curl -L -X POST 'https://ngw.devices.sberbank.ru:9443/api/v2/oauth' \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    -H 'Accept: application/json' \
    -H 'RqUID: <идентификатор_запроса>' \
    -H 'Authorization: Basic ключ_авторизации' \
    --data-urlencode 'scope=GIGACHAT_API_PERS'
    ```

    Где:

    * `RqUID` — обязательный заголовок, в котором нужно передать уникальный идентификатор запроса в формате `uuid4`. Идентификатор нужно указать самостоятельно, для этого можно использовать стандартные библиотеки и классы для генерации UUID и GUID.
    * `Authorization` — обязательный заголовок, в котором нужно передать [ключ авторизации](/ru/gigachat/quickstart/ind-using-api#poluchenie-avtorizatsionnyh-dannyh).
    * `scope` — обязательное поле в теле запроса, которое указывает к какой версии API выполняется запрос. Возможные значения:
      * `GIGACHAT_API_PERS` — доступ для физических лиц.
      * `GIGACHAT_API_B2B` — доступ для ИП и юридических лиц по [платным пакетам](/ru/gigachat/quickstart/legal-tokens-purchase#pokupka-paketov).
      * `GIGACHAT_API_CORP` — доступ для ИП и юридических лиц по схеме [pay-as-you-go](/ru/gigachat/quickstart/legal-tokens-purchase#oplata-pay-as-you-go).

    
    При успешном выполнении запроса GigaChat API вернет токен доступа, который действует в течение 30 минут:

    ```json
    {
      "access_token": "eyJhbGci3iJkaXIiLCJlbmMiOiJBMTI4R0NNIiwidHlwIjoiSldUIn0..Dx7iF7cCxL8SSTKx.Uu9bPK3tPe_crdhOJqU3fmgJo_Ffvt4UsbTG6Nn0CHghuZgA4mD9qiUiSVC--okoGFkjO77W.vjYrk3T7vGM6SoxytPkDJw",
      "expires_at": 1679471442
    }
    ```

    Запросы на получение токена можно отправлять до 10 раз в секунду.

    :::note

    Как получить ключ авторизации и токен доступа Access token читайте в разделах [Быстрый старт для физических лиц](/ru/gigachat/individuals-quickstart) и [Быстрый старт для ИП и юридических лиц](/ru/gigachat/legal-quickstart).

    :::

    ## Обращение к моделям в раннем доступе

    Модели для генерации GigaChat регулярно обновляются и у них появляются новые возможности, например, вызов функций.
    В таких случаях новые версии моделей некоторое время доступны в раннем доступе.

    Подробнее — в разделе [Модели GigaChat](/ru/gigachat/models/preview-models).

servers:
- url: https://gigachat.devices.sberbank.ru/api/v1
tags:
- name: Авторизация
  description: Получение токена доступа для авторизации запросов.
- name: Модели
  description: Запросы для получения данных доступных моделей.
- name: Чат
  description: Обмен сообщениями с моделью и информация о лимите токенов.
- name: Функции
  description: |
    В этом разделе описаны методы, облегчающие работу с собственными функциями при работе GigaChat API.

    <details>
      <summary>Подробнее о функциях</summary>

    Функции — ключевой элемент для построения сложных решений с применением LLM, таких, как AI-агенты и ассистенты.
    Они представляют внешние инструменты (фрагменты кода), к которым могут обращаться модели GigaChat для решения задач пользователей.
    Модель не исполняет функции, но самостоятельно принимает решение о том как, когда и с какими параметрами их следует вызвать.
    При принятии решения о вызове функции модель исходит из доступных знаний, данных текущего разговора и описания функции.
    После обращения к функции модель может обработать результат ее работы.

    </details>

    <ViewMoreBlock>
      <ViewMoreCard
        title="Работа с функциями"
        description="Руководство по описанию и вызову собственных и встроенных функций"
        href="ru/gigachat/guides/function-calling"
      />
    </ViewMoreBlock>
- name: Хранилище файлов
  description: |
    В этом разделе описаны методы для работы с хранилищем файлов, которые можно использовать при запросах на генерацию.
    Хранилище позволяет:

    * [загружать файлы](/ru/gigachat/api/reference/rest/post-file). Загруженные файлы доступны только вам;
    * [получать список доступных файлов](/ru/gigachat/api/reference/rest/get-files);
    * [получать описание выбранного файла](/ru/gigachat/api/reference/rest/get-file);
    * [скачивать файлы изображений](/ru/gigachat/api/reference/rest/get-file-id);
    * [удалять файлы](/ru/gigachat/api/reference/rest/file-delete).
    
    Кроме загруженных файлов, в хранилище также сохраняются файлы изображений, сгенерированных при выполнении запроса [POST /chat/completions](/ru/gigachat/api/reference/rest/post-chat).

    Хранилище поддерживает текстовые документы и изображения разных форматов.

    <Tabs queryString="ext">
    <TabItem value="text" label="Текстовые документы" default>

    ```mdx-code-block
    <APITable colsWidth={['200px']}>
    ```

    | Формат | MIME-тип   |
    |--------|------------|
    | txt    | text/plain  |
    | doc    | application/vnd.openxmlformats-officedocument.wordprocessingml.document  |
    | docx   | application/msword |
    | pdf    | application/pdf  |
    | epub   | application/epub  |
    | ppt    | application/ppt  |
    | pptx   | application/pptx  |

    ```mdx-code-block
    </APITable>
    ```
        
    </TabItem>
    <TabItem value="image" label="Изображения" >

    ```mdx-code-block
    <APITable colsWidth={['200px']}>
    ```
        
    | Формат | MIME-тип   |
    |--------|------------|
    | jpg    | image/jpg  |
    | png    | image/png  |
    | tiff   | image/tiff |
    | bmp    | image/bmp  |

    ```mdx-code-block
    </APITable>
    ```
        
    </TabItem>
    </Tabs>

    На размеры файлов действуют ограничения:

    * максимальный размер одного текстового файла — 40 Мб;
    * максимальный размер одного изображения — 15 Мб.

    <ViewMoreBlock>
      <ViewMoreCard
        title="Обработка файлов"
        description="Примеры и способы работы с хранилищем файлов"
        href="ru/gigachat/guides/working-with-files"
      />
    </ViewMoreBlock>
- name: Мониторинг потребления
  description: |
    В разделе описаны методы, которые помогут вам оценить, сколько токенов будет потрачено на ваш запрос, а также узнать остаток токенов для работы с каждой из доступных моделей.

    <details>
      <summary>Подробнее о токенах</summary>

    Токен — единица измерения стоимости запросов к модели. Токен может быть символом, несколькими символами, фрагментом слова или словом целиком. В среднем в одном токене 3—4 символа, включая пробелы, знаки препинания и специальные символы.

    Кроме текста сообщений в токены преобразуется контент, который используются в контексте запроса. Например, текстовые файлы и изображения, описания функций или история сообщений из массива `messages`.

    </details>

    <ViewMoreBlock>
      <ViewMoreCard
        title="Статистка потребления токенов"
        description="Узнайте как посмотреть статистику в личном кабинете"
        href="ru/gigachat/guides/token-consumption"
      />
      <ViewMoreCard
        title="Подсчет токенов"
        description="Примеры оценки количества токенов в запросе"
        href="ru/gigachat/guides/counting-tokens"
      />
    </ViewMoreBlock>
paths:
  /oauth:
    post:
      tags:
        - Авторизация
      servers:
        - url: https://ngw.devices.sberbank.ru:9443/api/v2
      parameters:
        - name: RqUID
          in: header
          description: |
            Уникальный идентификатор запроса. Соответствует формату [`uuid4`](https://www.uuidgenerator.net/version4).

            Параметр для журналирования входящих вызовов и разбора инцидентов.
            Идентификатор нужно указать самостоятельно, для этого можно использовать стандартные библиотеки и классы для генерации UUID и GUID.

            Пример: `6f0b1291-c7f3-43c6-bb2e-9f3efb2dc98e`.
          required: true
          schema:
            type: string
            format: uuidv4
            pattern: (([0-9a-fA-F-]){36})
            example: 6f0b1291-c7f3-43c6-bb2e-9f3efb2dc98e
      requestBody:
         content:
            'application/x-www-form-urlencoded':
              schema:
               type: object
               properties:
                  scope: 
                    description: |
                      Версия API. Возможные значения:

                        * `GIGACHAT_API_PERS` — доступ для физических лиц.
                        * `GIGACHAT_API_B2B` — доступ для ИП и юридических лиц по [платным пакетам](/ru/gigachat/quickstart/legal-tokens-purchase#pokupka-paketov).
                        * `GIGACHAT_API_CORP` — доступ для ИП и юридических лиц по схеме [pay-as-you-go](/ru/gigachat/quickstart/legal-tokens-purchase#oplata-pay-as-you-go).
                    type: string
                    enum:
                      - GIGACHAT_API_PERS
                      - GIGACHAT_API_B2B
                      - GIGACHAT_API_CORP
                    example: GIGACHAT_API_PERS
               required:
                 - scope
      x-codeSamples:
        - lang: "Python"
          label: "gigachat"
          source: |
            from gigachat import GigaChat

            giga = GigaChat(
               credentials="<ключ_авторизации>",
            )

            response = giga.get_token()

            print(response)
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Token'
          description: OK
        '400':
          $ref: '#/components/responses/BadRequestFormat'
        '401':
          $ref: '#/components/responses/AuthUnauthorizedError'
      security:
        - Базовая аутентификация: [client_id, client_secret]
      operationId: postToken
      summary: Получить токен доступа
      description: |
        Возвращает токен доступа для авторизации запросов к API.
        Токен доступа действителен в течение 30 минут.
        Запросы на получение токена можно отправлять до 10 раз в секунду.

        В заголовке `Authorization` нужно передать ключ авторизации — строку, полученную в результате кодирования в base64 идентификатора (Client ID) и клиентского ключа (Client Secret) API.

        Консоль запросов автоматически кодирует заданные идентификатор и клиентский ключ.

        :::note

        Как получить ключ авторизации и токен доступа Access token читайте в разделах [Быстрый старт для физических лиц](/ru/gigachat/individuals-quickstart) и [Быстрый старт для ИП и юридических лиц](/ru/gigachat/legal-quickstart).

        :::
  /tokens/count:
    post:
      tags:
        - Мониторинг потребления
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TokensCountBody'
      x-codeSamples:
        - lang: "Python"
          label: "gigachat"
          source: |
            from gigachat import GigaChat

            giga = GigaChat(
               credentials="<ключ_авторизации>",
            )

            response = giga.tokens_count(
                # Массив строк для подсчета токенов
                input_=["12345"],
                # Модель, которая используется для подсчета токенов
                model="GigaChat-Pro"
                )

            print(response)
        - lang: "TypeScript"
          label: "gigachat"
          source: |
            import GigaChat from 'gigachat';

            const giga = new GigaChat({
              credentials: '<ключ_авторизации>',
              scope: '<версия_API>',
            });

            const response = await giga.tokensCount(["Привет! Расскажи о себе в двух словах"]);

            console.log("Количество токенов в запросе: ", response.tokens[0].tokens);
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TokensCount'
          description: OK
        '401':
          $ref: '#/components/responses/UnauthorizedError'
      security:
        - Токен доступа: []
      operationId: postTokensCount
      summary: Подсчитать количество токенов
      description: Возвращает объект с информацией о количестве токенов, подсчитанных заданной моделью в строках. Строки передаются в массиве `input`.
  /balance:
    get:
      tags:
        - Мониторинг потребления
      parameters:
        - $ref: '#/components/parameters/xRequestId'
        - $ref: '#/components/parameters/xSessionId'
      x-codeSamples:
        - lang: "Python"
          label: "gigachat"
          source: |
            from gigachat import GigaChat

            giga = GigaChat(
               credentials="<ключ_авторизации>"
            )

            # Метод доступен только если вы используете пакеты токенов (купленные или бесплатные)
            response = giga.get_balance()

            print(response)
        - lang: "TypeScript"
          label: "gigachat"
          source: |
            import GigaChat from 'gigachat';

            const giga = new GigaChat({
              credentials: '<ключ_авторизации>',
              scope: '<версия_API>',
            });

            # Метод доступен только если вы используете пакеты токенов (купленные или бесплатные)
            const response = await giga.balance();

            console.log("Остаток токенов: ", response);
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Balance'
          description: OK
        '401':
          $ref: '#/components/responses/UnauthorizedError'
        '403':
          $ref: '#/components/responses/PermissionDeniedError'
      security:
        - Токен доступа: []
      operationId: getBalance
      summary: Получить остаток токенов
      description: |
        Возвращает доступный остаток токенов для каждой из моделей.
        Метод доступен только при покупке пакетов токенов.
        Если вы оплачиваете работу с API по схеме [pay-as-you-go](/ru/gigachat/api/tariffs#oplata-pay-as-you-go), запрос вернет ошибку 403 Permission Denied.

        Подробнее о пакетах токенов — в разделах платные пакеты для [физических лиц](/ru/gigachat/api/tariffs#platnye-pakety) или [для ИП и юридических лиц](/ru/gigachat/api/tariffs#platnye-pakety2).
  /models:
    get:
      tags:
        - Модели
      x-codeSamples:
        - lang: "Python"
          label: "gigachat"
          source: |
            from gigachat import GigaChat

            giga = GigaChat(
               credentials="<ключ_авторизации>",
            )

            response = giga.get_models()

            print(response)
        - lang: "TypeScript"
          label: "gigachat"
          source: |
            import GigaChat from 'gigachat';

            const giga = new GigaChat({
                credentials: '<ключ_авторизации>',
                scope: '<версия_API>',
            });

            const response = await giga.getModels();

            console.log(response);
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Models'
          description: OK
        '401':
          $ref: '#/components/responses/UnauthorizedError'
      security:
        - Токен доступа: []
      operationId: getModels
      summary: Получить список моделей
      description: Возвращает массив объектов с данными доступных моделей. Описание доступных моделей в разделе [Модели GigaChat](/ru/gigachat/models).
  /files:
    get:
      tags:
        - Хранилище файлов
      x-codeSamples:
        - lang: "Python"
          label: "gigachat"
          source: |
            from gigachat import GigaChat

            giga = GigaChat(
               credentials="<ключ_авторизации>"
            )

            response = giga.get_files()

            print(response)
        - lang: "TypeScript"
          label: "gigachat"
          source: |
            import GigaChat from 'gigachat';

            const giga = new GigaChat({
              credentials: '<ключ_авторизации>',
              scope: '<версия_API>',
            });

            const files = await giga.getFiles();

            console.log(files);
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Files'
          description: OK
      security:
        - Токен доступа: []
      operationId: getFiles
      summary: Получить список доступных файлов
      description: Возвращает массив объектов с данными доступных файлов.
    post:
      requestBody:
        content:
          multipart/form-data:
            schema:
              $ref: '#/components/schemas/FileUpload'
        required: true
      tags:
        - Хранилище файлов
      x-codeSamples:
        - lang: "Python"
          label: "gigachat"
          source: |
            from gigachat import GigaChat

            giga = GigaChat(
               credentials="<ключ_авторизации>",
            )

            response = giga.upload_file(open("/<путь_к_файлу>/<имя_файла>.txt", mode="rb"))

            print(response)
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/File'
          description: OK
      security:
        - Токен доступа: []
      operationId: postFile
      summary: Загрузить файл
      description: |
        Загружает в хранилище текстовые документы или изображения.
        Возвращает объект с данными загруженного файла.
        Загруженные файлы доступны только вам.

        Идентификатор файла, указанный в поле `id`, можно использовать при [запросах на генерацию](/ru/gigachat/api/reference/rest/post-chat).
        Для этого идентификаторы нужно передать в массиве `attachments`.
        Подробнее — в разделе [Обработка файлов](/ru/gigachat/guides/working-with-files).

        Хранилище поддерживает текстовые документы и изображения разных форматов.

        <Tabs queryString="ext">
        <TabItem value="text" label="Текстовые документы" default>

        ```mdx-code-block
        <APITable colsWidth={['200px']}>
        ```

        | Формат | MIME-тип   |
        |--------|------------|
        | txt    | text/plain  |
        | doc    | application/vnd.openxmlformats-officedocument.wordprocessingml.document  |
        | docx   | application/msword |
        | pdf    | application/pdf  |
        | epub   | application/epub  |
        | ppt    | application/ppt  |
        | pptx   | application/pptx  |

        ```mdx-code-block
        </APITable>
        ```
        
        </TabItem>
        <TabItem value="image" label="Изображения" >

        ```mdx-code-block
        <APITable colsWidth={['200px']}>
        ```
        
        | Формат | MIME-тип   |
        |--------|------------|
        | jpg    | image/jpg  |
        | png    | image/png  |
        | tiff   | image/tiff |
        | bmp    | image/bmp  |

        ```mdx-code-block
        </APITable>
        ```
        
        </TabItem>
        </Tabs>

        На размеры файлов действуют ограничения:

        * максимальный размер одного текстового файла в запросе — 40 Мб;
        * максимальный размер одного изображения в запросе — 15 Мб.
  /files/{file}:
    get:
      tags:
        - Хранилище файлов
      parameters:
        - name: file
          description: Идентификатор файла. Идентификатор содержится в поле найти в поле `id` объекта, который создается при загрузке файла в хранилище.
          schema:
            type: string
          in: path
          required: true
      x-codeSamples:
        - lang: "Python"
          label: "gigachat"
          source: |
            from gigachat import GigaChat

            giga = GigaChat(
               credentials="<ключ_авторизации>"
            )

            response = giga.get_file("<идентификатор_файла>")

            print(response)
        - lang: "TypeScript"
          label: "gigachat"
          source: |
            import GigaChat from 'gigachat';

            const giga = new GigaChat({
              credentials: '<ключ_авторизации>',
              scope: '<версия_API>',
            });

            const file = await giga.getFile('<идентификатор_файла>');

            console.log(file);
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/File'
          description: OK
      security:
        - Токен доступа: []
      operationId: getFile
      summary: Получить информацию о файле
      description: Возвращает объект с описанием указанного файла.
  /files/{file_id}/content:
    get:
      tags:
        - Хранилище файлов
      parameters:
        - name: file_id
          description: |
            Идентификатор изображения, полученный в ответ на запрос пользователя о генерации изображений.
            Содержится в ответе модели, в теге `<img>`, в атрибуте `src`.

            Подробнее в разделе [Генерация изображений](/ru/gigachat/guides/images-generation).
          schema:  
            type: string
          in: path
          required: true
        - in: header
          name: X-Client-ID
          schema:
            type: string
            description: |
              Идентификатор пользователя, который был передан в заголовке запроса на создание изображения [`GET /files/{file_id}/content`](/ru/gigachat/api/reference/rest/get-file-id).

              Если запрос на создание изображения содержал заголовок `X-Client-ID`, то такой же заголовок нужно передавать в запросе на скачивание файла.
      responses:
        '200':
          content:
            image/jpg: {}
          description: OK
        '400':
          description: Invalid model ID
        '401':
          $ref: '#/components/responses/UnauthorizedError'
        '404':
          $ref: '#/components/responses/NoSuchModel'
      security:
        - Токен доступа: []
      operationId: getFileId
      summary: Скачать файл
      description: |
        Возвращает файл изображения в бинарном представлении в формате JPG.

        Изображения создаются с помощью запроса [`POST /chat/completions`](/ru/gigachat/api/reference/rest/post-chat).

        Подробнее читайте в разделе [Создание изображений](/ru/gigachat/guides/images-generation).
        
        :::note

        Консоль запроса отключена из-за бинарного формата ответа.

        :::
  /files/{file}/delete:
    post:
      tags:
        - Хранилище файлов
      parameters:
        - name: file
          description: Идентификатор файла, который нужно удалить
          schema:
            type: string
          in: path
          required: true
      x-codeSamples:
        - lang: "Python"
          label: "gigachat"
          source: |
            from gigachat import GigaChat

            giga = GigaChat(
               credentials="<ключ_авторизации>"
            )

            response = giga.delete_file("<идентификатор_файла>")

            print(response)
        - lang: "TypeScript"
          label: "gigachat"
          source: |
            import GigaChat from 'gigachat';

            const giga = new GigaChat({
              credentials: '<ключ_авторизации>',
              scope: '<версия_API>',
            });

            const response = await giga.deleteFile('<идентификатор_файла>');

            console.log(response);
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/FileDeleted'
      security:
        - Токен доступа: []
      operationId: fileDelete
      summary: Удалить файл
      description: Переводит статус файла в значение `deleted`.
  /chat/completions:
    post:
      parameters:
        - $ref: '#/components/parameters/xClientId'
        - $ref: '#/components/parameters/xRequestId'
        - $ref: '#/components/parameters/xSessionId'
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Chat'
              example: {"model": "GigaChat","messages": [{"role": "system","content": "Ты профессиональный переводчик на английский язык. Переведи точно сообщение пользователя."},{"role": "user","content": "GigaChat — это сервис, который умеет взаимодействовать с пользователем в формате диалога, писать код, создавать тексты и картинки по запросу пользователя."}],"stream": false,"update_interval": 0}
      x-codeSamples:
        - lang: "Python"
          label: "gigachat"
          source: |
            from gigachat import GigaChat

            giga = GigaChat(
               credentials="<ключ_авторизации>",
            )

            response = giga.chat("Расскажи про себя")

            print(response)
        - lang: "TypeScript"
          label: "gigachat"
          source: |
            import GigaChat from 'gigachat';

            const giga = new GigaChat({
              credentials: '<ключ_авторизации>',
              scope: '<версия_API>',
            });

            giga.chat({
                messages: [
                  {
                     role: 'user',
                     content: 'Привет! Расскажи о себе в двух словах'
                  }
                ],
              })
              .then((resp) => {
                console.log(resp.choices[0]?.message.content);
              });
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ChatCompletion'
          description: OK
        '400':
          $ref: '#/components/responses/BadRequestFormat'
        '401':
          $ref: '#/components/responses/UnauthorizedError'
        '404':
          $ref: '#/components/responses/NoSuchModel'
        '422':
          $ref: '#/components/responses/ValidationError'
        '429':
          $ref: '#/components/responses/TooManyRequests'
        '500':
          $ref: '#/components/responses/InternalError'
      security:
        - Токен доступа: []
      operationId: postChat
      summary: Получить ответ модели на сообщения
      description: |
        Возвращает ответ модели, сгенерированный на основе переданных сообщений.

        Передавайте текст сообщений (поле `content`) в кодировке UTF8.
        Это позволит снизить расход токенов при обработке сообщения.

        При генерации ответа модель может учитывать текстовые документы и изображения, сохраненные в хранилище.
        Для этого передайте список идентификаторов файлов в массиве `attachments`.
        В одном сообщении (объект в массиве `messages`) можно передать только одно изображение.
        В одном запросе можно передать до 10 изображений, независимо от количества сообщений.
        
        :::note
        
        При этом общий размер запроса должен быть меньше 20 Мб.

        Например, ваш запрос может включать текст промпта и два идентификатора изображений, которые ссылаются на файлы размерами 6 Мб и 12 Мб.

        :::

        Подробнее — в разделе [Обработка файлов](/ru/gigachat/guides/working-with-files).

        Запрос на генерацию можно передавать [моделям в раннем доступе](/ru/gigachat/models#obrashenie-k-modelyam-rannego-dostupa).
        К названию модели, которое передается в поле `model`, добавьте постфикс `-preview`.
  /ai/check:
    post:
      parameters:
        - $ref: '#/components/parameters/xClientId'
        - $ref: '#/components/parameters/xRequestId'
        - $ref: '#/components/parameters/xSessionId'
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/aiCheck'
      x-codeSamples:
        - lang: "TypeScript"
          label: "gigachat"
          source: |
            import GigaChat from 'gigachat';

            const giga = new GigaChat({
                credentials: 'ключ_авторизации',
            });

            const response = await giga.aiCheck('<текст_для_проверки>', '<название_модели>');

            console.log(response);
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/aiCheckResponse'
                example: {"category": "mixed",  "characters": 500,  "tokens": 38,  "ai_intervals": [    [0, 100],    [150, 200]  ]}
          description: OK
      security:
        - Токен доступа: []
      operationId: postAiCheck
      summary: Проверить, написан ли текст ИИ
      description: |
        Проверяет переданный текст на наличие содержимого, сгенерированного с помощью нейросетевых моделей.
        Проверка доступна только для текстов на русском языке.
        Минимальная длина текста — 20 слов.

        Метод доступен только для юридических лиц, которые работают по схеме оплаты [pay-as-you-go](/ru/gigachat/api/tariffs#oplata-pay-as-you-go).
  /embeddings:
    post:
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/EmbeddingsBody'
      x-codeSamples:
        - lang: "Python"
          label: "gigachat"
          source: |
            from gigachat import GigaChat

            giga = GigaChat(
               credentials="<ключ_авторизации>"
            )

            response = giga.embeddings(["Hello world!"])

            print(response)
        - lang: "TypeScript"
          label: "gigachat"
          source: |
            import GigaChat from 'gigachat';

            const giga = new GigaChat({
                credentials: 'ключ_авторизации',
            });

            const response = await giga.embeddings(['Слова слова слова']);

            console.log(response.data);
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Embedding'
          description: OK
        '401':
          $ref: '#/components/responses/UnauthorizedError'
      security:
        - Токен доступа: []
      operationId: postEmbeddings
      summary: Создать эмбеддинг
      description: |
        Возвращает векторные представления соответствующих текстовых запросов. Индекс объекта с векторным представлением (поле `index`) соответствует индексу строки в массиве `input` запроса.

        Векторное представление выглядит как массив чисел `embedding`. Каждое значение в массиве представляет одну из характеристик или признаков текста, учтенных при вычислении эмбеддинга. Значения образуют числовое представление текста и позволяют анализировать и использовать текст в различных задачах. Как правило, чем ближе значения эмбеддингов друг к другу, тем более семантически близки тексты.

        Для создания эмбеддингов можно использовать [модели Embeddings и EmbeddingsGigaR](/ru/gigachat/models#model-dlya-vektornogo-predstavleniya-teksta).
        Запросы [тарифицируются](/ru/gigachat/api/tariffs) одинаково, независимо от использованной модели.

        :::tip

        Для улучшения результатов при работе с моделью EmbeddingsGigaR следуйте рекомендациям в разделе [Векторное представление текста](/ru/gigachat/guides/embeddings#embeddingsgigar-recommendations).

        :::
  /functions/validate:
    post:
      parameters:
        - $ref: '#/components/parameters/xRequestId'
        - $ref: '#/components/parameters/xSessionId'
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CustomFunction'
      tags:
        - Функции
      responses:
        '200':
          description: |
            Результат валидации функции.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/FunctionValidationResult'
        '400':
          $ref: '#/components/responses/BadRequestFormat'
        '401':
          $ref: '#/components/responses/UnauthorizedError'
        '429':
          $ref: '#/components/responses/TooManyRequests'
        '500':
          $ref: '#/components/responses/InternalError'
      security:
        - Токен доступа: []
      operationId: functionValidation
      summary: Валидировать функцию
      description: |
        Проверяет переданное описание функции на соответствие формату функций GigaChat.
        
        Пример описания функции GigaChat — в массиве `functions`, в запросе [`POST /chat/completions`](/ru/gigachat/api/reference/rest/post-chat).

        Метод принимает описание функции в формате JSON.
        
        В результате проверки возвращается массив ошибок и предупреждений, которые нужно исправить, чтобы описание функции соответствовало формату GigaChat.

        <details>
        <summary>Пример описания функции в формате JSON Schema</summary>

        ```json
        {
            "name": "send_sms",
            "description": "Отправка SMS контакту по ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "contactId": {
                        "description": "ID контакта",
                        "format": "int32",
                        "type": "integer"
                    },
                    "text": {
                        "description": "Текст SMS",
                        "minLength": 1,
                        "type": "string"
                    },
                    "version": {
                        "description": "Описание параметра - версия API",
                        "type": "string"
                    }
                },
                "required": [
                    "version",
                    "contactId",
                    "text"
                ]
            },
            "return_parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "description": "Описание статуса",
                        "nullable": true,
                        "type": "string"
                    },
                    "phone": {
                        "description": "Номер: маска + 2 последние цифры номера",
                        "nullable": true,
                        "type": "string"
                    },
                    "status": {
                        "description": "Отправлено/не отправлено",
                        "type": "boolean"
                    }
                }
            },
            "few_shot_examples": [
                {
                    "request": "Отправь SMS контакту с ID 111111 с текстом Hello World",
                    "params": {
                        "contactId": "111111",
                        "text": "Hello world"
                    }
                }
            ]
        }
        ```
        </details>

        Подробнее — в разделе [Работа с функциями](/ru/gigachat/guides/function-calling).
components:
  parameters:
    xClientId:
      name: X-Client-ID
      in: header
      schema:
        type: string
        description: |
          Произвольный идентификатор пользователя, который используется для логирования.

          Если вы передали этот заголовок при запросе на создание изображения, то для скачивания изображения в запросе [`GET /files/{file_id}/content`](/ru/gigachat/api/reference/rest/get-file-id) нужно передать этот же заголовок.
    xRequestId:
      in: header
      name: X-Request-ID
      schema:
        type: string
        description: Произвольный идентификатор запроса, который используется для логирования.
    xSessionId:
      in: header
      name: X-Session-ID
      schema:
        type: string
        description: Произвольный идентификатор сессии, который используется для логирования.
  schemas:
    FunctionValidationResult:
      type: object
      description: Объект с результатом валидации функции, описанной в формате JSON.
      properties:
        status:
          type: integer
          default: 200
          description: HTTP-код ответа.
        message:
          type: string
          description: |
            Сообщение о результате валидации функции.
            Возможные значения:

            * `Function is valid` — описание функции полностью соответствует формату GigaChat API или содержит незначительные проблемы (блок `warnings`).
            * `Incorrect function syntax` — описание функции не соответствует формату GigaChat API (ответ содержит блок `errors`).
          enum:
            - Function is valid
            - Incorrect function syntax
        json_ai_rules_version:
          type: string
          description: |
            Версия правил, которые используются для валидации функции.

            Передается, если запрос содержит описание функции в формате JSON.
          example: 1.0.5
        errors:
          description: |
            Массив с описанием ошибок, возникших при валидации функции.
            В отличие от предупреждений ошибки возникают, когда описание функции нарушает формат GigaChat API.
            Например, если в описании отсутствуют обязательные блоки `name` или `parameters`.

            Если в описании функции есть ошибки (массив `errors`), то предупреждения (массив `warnings`) не передаются.

            Перед отправкой функции в запросе [`POST /chat/completions`](/ru/gigachat/api/reference/rest/post-chat) ошибки нужно исправить.
          type: array
          items:
            type: object
            properties:
              description:
                type: string
                description: Описание ошибки.
                example: name is required
              schema_location:
                type: string
                description: Указывает, где в схеме нужно внести изменения, чтобы исправить ошибку.
                example: (root)
        warnings:
          description: |
            Массив с описанием предупреждений, возникших при валидации функции.
            В отличие от предупреждений ошибки возникают, когда описание функции нарушает формат GigaChat API.
            Например, если в описании отсутствует необязательный массив образцов `few_shot_examples are missing`.

            Предупреждения (массив `warnings`) не передаются, если в описании функции есть ошибки (массив `errors`).
          type: array
          items:
            type: object
            properties:
              description:
                type: string
                description: Описание предупреждения.
                example: few_shot_examples are missing
              schema_location:
                type: string
                description: Указывает, где в схеме нужно внести изменения, чтобы исправить предупреждения.
                example: (root)
    CustomFunctions:
      type: array
      description: Массив с описанием пользовательских функций.
      items:
        $ref: '#/components/schemas/CustomFunction'
    CustomFunction:
      description: Описание пользовательской функции.
      type: object
      required:
        - "name"
        - "parameters"
      properties:
        name:
          type: string
          description: Название пользовательской функции, для которой будут сгенерированы аргументы.
          example: pizza_order
        description:
          type: string
          description: Текстовое описание функции.
          example: Функция для заказа пиццы
        parameters:
          type: object
          properties: {}
          description: Валидный JSON-объект с набором пар `ключ-значение`, которые описывают аргументы функции.
        few_shot_examples:
          type: array
          description: |
            Объекты с парами `запрос_пользователя`-`параметры_функции`, которые будут служить модели примерами ожидаемого результата.
          items:
            type: object
            required:
              - "request"
              - "params"
            properties:
              request:
                type: string
                description: Запрос пользователя.
                example: Погода в Москве в ближайшие три дня
              params:
                type: object
                description: Пример заполнения параметров пользовательской функции.
                properties: {}
        return_parameters:
          type: object
          description: JSON-объект с описанием параметров, которые может вернуть ваша функция.
          properties: {}
    Model:
      type: object
      properties:
        id:
          description: |
            Название и версия модели, которая сгенерировала ответ. Описание доступных моделей смотрите в разделе [Модели GigaChat](https://developers.sber.ru/docs/ru/gigachat/models).

            При обращении к моделям в раннем доступе к названию модели нужно добавлять постфикс `-preview`.
            Например, `GigaChat-Pro-preview`.
          type: string
          example: GigaChat:1.0.26.20
        object:
          description: Тип сущности в ответе, например, модель.
          type: string
          example: model
        owned_by:
          description: Владелец модели
          type: string
          example: salutedevices
        type:
          description: Тип модели. Значение `chat` указывает, что модель используется для генерации.
          default: chat
    ModelId:
      type: object
      properties:
        model:
          $ref: '#/components/schemas/Model/properties/id'
    Models:
      type: object
      properties:
        data:
          type: array
          items:
            $ref: '#/components/schemas/Model'
        object:
          description: Тип сущности в ответе, например, список.
          type: string
          example: list
    aiCheck:
      type: object
      required: 
      - model
      - input
      properties:
        input:
          type: string
          description: |
            Текст, который будет проверен на наличие содержимого, сгенерированного с помощью нейросетевых моделей.
            Проверка доступна только для текстов на русском языке.
            Минимальная длина текста — 20 слов.
          example: Первый искусственный спутник Земли был запущен Советским Союзом 4 октября 1957 года. Этот исторический запуск ознаменовал начало космической эры и стал важным событием в истории человечества. Спутник получил название «Спутник-1».
        model:
          type: string
          enum:
          - GigaCheckClassification
          - GigaCheckDetection
          description: |
            Название модели.
            Модель GigaCheckClassification лучше всего подходит для анализа и разделения текста на два класса: написанный человеком или сгенерированный нейросетью (`ai`/`human`). В модели GigaCheckDetection добавляется третий класс — `mixed` (`ai`+`human`), что позволяет определять тексты, частично созданные с помощью ИИ.
          example: "GigaCheckClassification"
    aiCheckResponse:
      type: object
      properties:
        category:
          type: string
          description: |
            Результат проверки текста. Возможные значения:

            * `ai` — текст сгенерирован с помощью нейросетевых моделей;
            * `human` — текст написан человеком;
            * `mixed` — текст содержит как фрагменты сгенерированные с помощью моделей, так и написанные человеком.
          enum:
            - ai
            - human
            - mixed
          example: ai
        characters:
          type: integer
          description: Количество символов в переданном тексте.
          example: 158
        tokens:
          type: integer
          description: Количество токенов в переданном тексте.
          example: 38
        ai_intervals:
          type: array
          items:
            type: array
          description: |
            Части текста, сгенерированные моделью.
            Обозначаются индексами символов, с которых начинаются и заканчиваются сгенерированные фрагменты.

            Содержит пустой массив если текст полностью сгенерирован с помощью нейросетевых моделей (`"category": "ai"`) или написан человеком (`"category": "human"`).
    Balance:
      type: object
      properties:
        balance:
          type: array
          items:
            type: object
            properties:
              usage:
                type: string
                description: Название модели, например, GigaChat или embeddings. 
                example: GigaChat
              value:
                type: integer
                description: Остаток токенов
                example: 100500
    File:
      description: Описание файла, доступного в хранилище
      required:
        - id
        - object
        - bytes
        - created_at
        - filename
        - purpose
      type: object
      properties:
        bytes:
          description: Размер файла в байтах
          type: integer
          example: 120000
        created_at:
          description: Время создания файла в формате unix timestamp.
          type: integer
          format: unix timestamp
          example: 1677610602
        filename:
          description: Название файла
          type: string
          example: file123
        id:
          description: |
            Идентификатор файла, который можно использовать при [запросах на генерацию](/ru/gigachat/api/reference/rest/post-chat).
            Для этого идентификаторы нужно передать в массиве `attachments`.
            
            Подробнее — в разделе [Обработка файлов](/ru/gigachat/guides/working-with-files).
          type: string
          format: uuidv4
          pattern: (([0-9a-fA-F-])36)
          example: 6f0b1291-c7f3-43c6-bb2e-9f3efb2dc98e
        object:
          description: Тип объекта
          type: string
          example: file
        purpose:
          description: Назначение файлов. Значение `general` указывает на то, что файлы могут использоваться для [генерации ответа модели](/ru/gigachat/guides/working-with-files)
          enum:
            - general
          type: string
        access_policy:
          type: string
          description: |
            Доступность файла возможные значения:
            
            * `public`;
            * `private`.
          example: private
          default: private
          enum:
            - public
            - private  
    Files:
      description: Массив объектов с данными доступных файлов
      required:
        - data
      type: object
      properties:
        data:
          type: array
          items:
            $ref: '#/components/schemas/File'
    FileUpload:
      required:
        - file
        - purpose
      type: object
      properties:
        file:
          format: binary
          description: Загружаемый объект
          type: string
        purpose:
          description: Назначение загружаемого файла
          enum:
            - general
          type: string
          default: general
    FileDeleted:
      type: object
      properties:
        id:
          type: string
          description: Идентификатор файла
          example: d3277ca1-a140-484a-a3b4-9a121bea4bdc
        deleted:
          type: boolean
          description: Признак удаления файла
          example: true
    FileAccessPolicy:
      type: object
      required:
        - file_ids
        - access_policy
      properties:
        file_ids:
          type: array
          description: Массив идентификаторов файлов
          items:
            type: string
        access_policy:
          type: string
          enum:
            - public
            - private
          description: Доступность файла       
    FileId:
      required:
        - file_id
      type: object
      properties:
        file_id:
          description: |
            Идентификатор созданного изображения, полученный в ответ на запрос пользователя.
            Содержится в ответе модели, в теге `<img>`, в атрибуте `src`.

          # Подробнее в разделе [Генерация изображений](/ru/gigachat/guides/images-generation).
          type: string
          example: 7wy0e9934sbjc09snz40c2gf1mej42ra0r00d8yz4d47r0adb17281t3096qpnamb4eqc1t3bd7qj1jman5q2mtzawfqrmgtbd7dv2bx54
    Chat:
      required:
        - model
        - messages
      type: object
      properties:
        model:
          $ref: '#/components/schemas/Model/properties/id'
        messages:
          type: array
          description: Массив сообщений, которыми пользователь обменивался с моделью.
          items:
            $ref: '#/components/schemas/message'
        function_call:
          description: |
            Поле, которое отвечает за то, как GigaChat будет [работать с функциями](/ru/gigachat/guides/function-calling).
            Может быть строкой или объектом.

            Возможные значения:

            * `none` — режим работы по умолчанию. Если запрос не содержит `function_call` или значение поля — `none`, GigaChat не вызовет функции, а просто сгенерирует ответ в соответствии с полученными сообщениями;

            * `auto` — в зависимости от содержимого запроса, модель решает сгенерировать сообщение или вызвать функцию.
            Модель вызывает встроенные функции, если отсутствует массив `functions` с описанием пользовательских функций.
            Если запрос содержит `"function_call": "auto"` и массив `functions` с описанием пользовательских функций, модель будет генерировать аргументы для описанных функций и не сможет вызвать встроенные функции независимо от содержимого запроса;
            
            * `{"name": "название_функции"}` — принудительная генерация аргументов для указанной функции. Вы можете явно задать часть аргументов с помощью объекта `partial_arguments`. Остальные аргументы модель сгенерирует самостоятельно. При принудительной генерации, массив `functions` обязан содержать объект с описанием указанной функции. В противном случае вернется ошибка.
          oneOf:
            - $ref: '#/components/schemas/function_call_custom_function'
            - $ref: '#/components/schemas/function_call_none_auto'
        functions:
          $ref: '#/components/schemas/CustomFunctions'
        temperature:
          format: float
          type: number
          description: |
            Температура выборки. Чем выше значение, тем более случайным будет ответ модели. Если значение температуры находится в диапазоне от 0 до 0.001, параметры `temperature` и `top_p` будут сброшены в режим, обеспечивающий максимально детерминированный (стабильный) ответ модели. При значениях температуры больше двух, набор токенов в ответе модели может отличаться избыточной случайностью.

            Значение по умолчанию зависит от выбранной модели (поле `model`) и может изменяться с обновлениями модели.
          minimum: 0
          exclusiveMinimum: true
        top_p:
          format: float
          type: number
          description: |
            Параметр используется как альтернатива температуре (поле `temperature`). Задает вероятностную массу токенов, которые должна учитывать модель.
            Так, если передать значение 0.1, модель будет учитывать только токены, чья вероятностная масса входит в верхние 10%.

            Значение по умолчанию зависит от выбранной модели (поле `model`) и может изменяться с обновлениями модели.

            Значение изменяется в диапазоне от 0 до 1 включительно.
          minimum: 0
          maximum: 1
        stream:
          type: boolean
          description: |
            Указывает что сообщения надо передавать по частям в потоке.

            Сообщения передаются по протоколу [SSE](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#event_stream_format).

            Поток завершается событием `data: [DONE]`.

            Подробнее читайте в разделе [Потоковая генерация токенов](/ru/gigachat/guides/response-token-streaming).
          default: false
          example: false
        max_tokens:
          description: Максимальное количество токенов, которые будут использованы для создания ответов.
          format: int32
          type: integer
        repetition_penalty:
          type: number
          format: float
          description: |
            Количество повторений слов:
            
            * Значение 1.0 — нейтральное значение.
            * При значении больше 1 модель будет стараться не повторять слова.

            Значение по умолчанию зависит от выбранной модели (поле `model`) и может изменяться с обновлениями модели.
          example: 1.0
        update_interval:
          type: number
          description: |
            Параметр потокового режима (`"stream": "true"`).
            Задает минимальный интервал в секундах, который проходит между отправкой токенов.
            Например, если указать `1`, сообщения будут приходить каждую секунду, но размер каждого из них будет больше, так как за секунду накапливается много токенов.
          default: 0
          example: 0
    message:
      type: object
      properties:
        role:
          type: string
          description: |
            Роль автора сообщения:

            * `system` — системный промпт, который задает роль модели, например, должна модель отвечать как академик или как школьник;
            * `assistant` — ответ модели;
            * `user` — сообщение пользователя;
            * `function` — сообщение с результатом работы [пользовательской функции](/ru/gigachat/guides/function-calling#rabota-s-sobstvennymi-funktsiyami). В сообщении с этой ролью передавайте результаты работы функции в поле `content` в форме валидного JSON-объекта, обернутого в строку.

            Для сохранения контекста диалога с пользователем передайте несколько сообщений. Подробнее читайте в разделе [Работа с историей чата](/ru/gigachat/guides/keeping-context).
          enum:
            - system
            - user
            - assistant
            - function
          example: function
        content:
          description: |
            Содержимое сообщения. Зависит от роли.

            Если поле передается в сообщении с ролью `function`, то в нем указывается обернутый в строку валидный JSON-объект с аргументами функции, указанной в поле `function_call.name`.

            В остальных случаях содержит либо системный промпт (сообщение с ролью `system`), либо текст сообщения пользователя или модели.

            Передавайте текст в кодировке UTF8.
            Это позволит снизить расход токенов при обработке сообщения.
          type: string
          example: "{\"temperature\": \"27\"}"
        functions_state_id:
          type: string
          format: uuidv4
          description: |
            Идентификатор, который объединяет массив функций, переданных в запросе.
            Возвращается в ответе модели (сообщение с `"role": "assistant"`) при вызове встроенных или собственных функций.
            Позволяет сохранить [контекст вызова функции](/ru/gigachat/guides/function-calling#sohranenie-konteksta) и повысить качество работы модели.
            Для этого нужно передать идентификатор в запросе на генерацию в сообщении с ролью `assistant`.

            Сейчас поле работает только при обращении к [моделям в раннем доступе](/ru/gigachat/models/preview-models).
          example: 77d3fb14-457a-46ba-937e-8d856156d003
        attachments:
          description: |
            Массив идентификаторов файлов, которые нужно использовать при генерации.
            Идентификатор присваивается файлу при [загрузке в хранилище](/ru/gigachat/api/reference/rest/post-file).
            Посмотреть список файлов в хранилище можно с помощью метода [`GET /files`](/ru/gigachat/api/reference/rest/get-files).

            При работе с текстовыми документами в одном запросе на генерацию нужно передавать только один идентификатор.
            Если вы передадите несколько идентификаторов файлов, для генерации будет использован только первый файл из списка.

            В одном сообщении (объект в массиве `messages`) можно передать только одно изображение.
            В одной сессии можно передать до 10 изображений.

            <Admonition type="note">
            
            При этом общий размер запроса должен быть меньше 20 Мб.

            Например, ваш запрос может включать текст промпта и два идентификатора изображений, которые ссылаются на файлы размерами 6 Мб и 12 Мб.

            </Admonition>

            Подробнее — в разделе [Обработка файлов](/ru/gigachat/guides/working-with-files)
          type: array
          items:
            type: string
            example: 
             - e7f0b84b-3d4f-4c2c-ac31-8855b1b0db0a
    MessagesRes:
      type: object
      description: Сгенерированное сообщение.
      properties:
        role:
          type: string
          enum:
            - assistant
            - function_in_progress
          description: |
            Роль автора сообщения.

            Роль `function_in_progress` используется при работе встроенных функций в режиме [потоковой передачи токенов](/ru/gigachat/guides/function-calling#potokovaya-peredacha-tokenov).
          example: assistant
        content:
          type: string
          description: |
            Содержимое сообщения, например, результат генерации.

            В сообщениях с ролью `function_in_progress` содержит информацию о том, сколько времени осталось до завершения работы встроенной функции.
          example: 'Здравствуйте! К сожалению, я не могу дать точный ответ на этот вопрос, так как это зависит от многих факторов. Однако обычно релиз новых функций и обновлений в GigaChat происходит постепенно и незаметно для пользователей. Рекомендую следить за новостями и обновлениями проекта в официальном сообществе GigaChat или на сайте разработчиков.'
        created:
          type: integer
          format: unix timestamp
          description: Передается в сообщениях с ролью`function_in_progress`. Содержит информацию о том, когда был создан фрагмент сообщения.
          example: 1625284800
        name:
          type: string
          description: Название вызванной встроенной функции. Передается в сообщениях с ролью`function_in_progress`.
          example: text2image
        functions_state_id:
          type: string
          format: uuidv4
          description: |
            Идентификатор, который объединяет массив функций, переданных в запросе.
            Возвращается в ответе модели (сообщение с `"role": "assistant"`) при вызове встроенных или собственных функций.
            Позволяет сохранить [контекст вызова функции](/ru/gigachat/guides/function-calling#sohranenie-konteksta) и повысить качество работы модели.
            Для этого нужно передать идентификатор в запросе на генерацию в сообщении с ролью `assistant`.

            Сейчас поле работает только при обращении к [моделям в раннем доступе](/ru/gigachat/models/preview-models).
          example: 77d3fb14-457a-46ba-937e-8d856156d003
        function_call: 
          type: object
          properties:
            name:
              type: string
              description: Название функции.
            arguments:
              type: object
              description: Аргументы для вызова функции в виде пар ключ-значение.
    Usage:
      type: object
      description: Данные об использовании модели.
      properties:
        prompt_tokens:
          format: int32
          description: Количество токенов во входящем сообщении (роль `user`).
          type: integer
          example: 1
        completion_tokens:
          format: int32
          description: Количество токенов, сгенерированных моделью (роль `assistant`).
          type: integer
          example: 4
        precached_prompt_tokens:
          format: int32
          description: |
            Количество ранее закэшированных токенов, которые были использованы при обработке запроса.
            Кэшированные токены вычитаются из общего числа оплачиваемых токенов (поле `total_tokens`).

            Модели GigaChat в течение некоторого времени сохраняют контекст запроса (историю сообщений массива `messages`, описание функций) с помощью кэширования токенов. Это позволяет повысить скорость ответа моделей и снизить стоимость работы с GigaChat API.

            <Admonition type="tip">

            Для повышения вероятности использования сохраненных токенов используйте [кэширование запросов](/ru/gigachat/guides/keeping-context#keshirovanie-zaprosov).

            </Admonition>

            [Подробнее о подсчете токенов](/ru/gigachat/guides/counting-tokens).
          type: integer
          example: 37
        total_tokens:
          format: int32
          description: Общее число токенов, подлежащих тарификации, после вычитания кэшированных токенов (поле `precached_prompt_tokens`).
          type: integer
          example: 5
    ChatCompletion:
      type: object
      properties:
        choices:
          type: array
          description: Массив ответов модели.
          items:
            $ref: '#/components/schemas/Choices'
        created:
          format: unix timestamp
          type: integer
          description: Дата и время создания ответа в формате unix timestamp.
          example: 1678878333
        model:
          $ref: '#/components/schemas/Model/properties/id'
        usage:
          $ref: '#/components/schemas/Usage'
        object:
          type: string
          description: Название вызываемого метода.
          example: chat.completion
    Choices:
      type: object
      properties:
        message:
          $ref: '#/components/schemas/MessagesRes'    
        index:
          format: int32
          type: integer
          description: Индекс сообщения в массиве, начиная с ноля.
          example: 0
        finish_reason:
          description: |
            Причина завершения гипотезы. Возможные значения:
            
            * `stop` — модель закончила формировать гипотезу и вернула полный ответ;
            * `length` — достигнут лимит токенов в сообщении;
            * `function_call` — указывает, что при запросе была вызвана встроенная функция или сгенерированы аргументы для пользовательской функции;
            * `blacklist` — запрос попадает под [тематические ограничения](/ru/gigachat/limitations#tematicheskie-ogranicheniya-zaprosov).
            * `error` — ответ модели содержит невалидные аргументы пользовательской функции.
            
          type: string
          enum:
            - stop
            - length
            - function_call
            - blacklist
            - error
          example: "stop"
    Token:
      type: object
      properties:
        access_token:
          type: string
          description: Токен для авторизации запросов.
          example: >-
            eyJhbGci3iJkaXIiLCJlbmMiOiJBMTI4R0NNIiwidHlwIjoiSldUIn0..Dx7iF7cCxL8SSTKx.Uu9bPK3tPe_crdhOJqU3fmgJo_Ffvt4UsbTG6Nn0CHghuZgA4mD9qiUiSVC--okoGFkjO77W.vjYrk3T7vGM6SoxytPkDJw
        expires_at:
          format: unix timestamp в миллисекундах
          description: Дата и время истечения действия токена в миллисекундах, в формате unix timestamp.
          type: integer
          example: 1739784663483
    TokensCount:
      type: array
      items:
        type: object
        properties:
          object:
            type: string
            description: Описание того, какая информация содержится в объекте.
            default: tokens
          tokens:
            type: integer
            description: Количество токенов в соответствующей строке.
            example: 7
          characters:
            type: integer
            description: Количество символов в соответствующей строке.
            example: 36
    Embedding:
      type: object
      required:
        - "data"
        - "object"
      properties:
        object:
          type: string
          description: Формат структуры данных.
          default: list
        data:
          type: array
          items:
            type: object
            description: Объект с данными о векторном представлении текста.
            required:
              - "object"
              - "embedding"
              - "index"
              - "usage"
            properties:
              object:
                type: string
                description: Тип объекта.
                default: embedding
              embedding:
                type: array
                description: Массив чисел, представляющий значения эмбеддинга для предоставленного текста. 
                items:
                  type: integer
                  format: float
              index:
                type: integer
                description: Индекс, соответствующий индексу текста, полученного в массиве `input` запроса.
                example: 0
              usage:
                type: object
                properties:
                  prompt_tokens:
                    type: number
                    description: Количество токенов в строке, для которой сгенерирован эмбеддинг.
                    example: 6
        model:
          type: string
          description: Название модели, которая используется для вычисления эмбеддинга.
          example: Embeddings
    TokensCountBody:
      type: object
      required:
        - "model"
        - "input"
      properties:
        model:
          type: string
          description: Название модели, которая будет использована для подсчета количества токенов.
          enum:
            - GigaChat
            - GigaChat-Pro
            - GigaChat-Max
          example: GigaChat
        input:
          type: array
          description: Строка или массив строк, в которых надо подсчитать количество токенов.
          items:
            type: string
            example: Я к вам пишу — чего же боле?
    EmbeddingsBody:
      type: object
      required:
        - "input"
        - "model"
      properties:
        model:
          type: string
          description: |
            Название модели, которая будет использована для создания эмбеддинга.

            Возможные значения:

            * `Embeddings` — базовая модель, доступная по умолчанию для векторного представления текстов;
            * `EmbeddingsGigaR` — продвинутая модель с большим размером контекста.

            Запросы [тарифицируются](/ru/gigachat/api/tariffs) одинаково, независимо от использованной модели.

            Для улучшения результатов при работе с моделью EmbeddingsGigaR следуйте рекомендациям в разделе [Векторное представление текста](/ru/gigachat/guides/embeddings#embeddingsgigar-recommendations).
          example: Embeddings
        input:
          type: array
          description: Строка или массив строк, которые будут использованы для генерации эмбеддинга.
          items:
            type: string
            example: Расскажи о современных технологиях
    function_call_custom_function:
      type: object
      properties:
        name:
          type: string
          description: Название функции.
          example: sbermarket-pizza_order
        partial_arguments: 
          type: object
          description: JSON-объект в котором вы можете явно задать некоторые аргументы указанной функции. Остальные аргументы модель сгенерирует самостоятельно.
          properties: {}
    function_call_none_auto:
      type: string
      enum: 
        - auto
        - none
      description: Режим работы с функциями  
      example: auto 
  responses:
    AuthUnauthorizedError:
      description: Ошибка авторизации.
      content:
        application/json:
          schema:
            type: object
            properties:
              code:
                type: integer
                description: Код ошибки.
                example: 6
              message:
                type: string
                description: Описание ошибки.
                example: credentials doesn't match db data
    PermissionDeniedError:
      description: Ошибка доступа. Возникает при отправке запроса если вы оплачиваете работу с API по схеме [pay-as-you-go](/ru/gigachat/api/tariffs#oplata-pay-as-you-go).
      content:
        application/json:
          schema:
            type: object
            properties:
              status:
                 type: integer
                 description: HTTP-код сообщения.
                 default: 403
              message:
                type: string
                description: Описание ошибки.
                default: Permission denied
    UnauthorizedError:
      description: Ошибка авторизации.
      content:
        application/json:
          schema:
            type: object
            properties:
              status:
                 type: integer
                 description: HTTP-код сообщения.
                 default: 401
              message:
                type: string
                description: Описание ошибки.
                default: Unauthorized
    TokenExpired:
      description: Истек срок действия токена.
      content:
        application/json:
          schema:
            type: object
            properties:
              status:
                 type: integer
                 description: HTTP-код сообщения.
                 default: 401
              message:
                type: string
                description: Описание ошибки.
                default: Token has expired
    ModelNotFound:
      description: Model with id <model_id> not found
    NoSuchModel:
      description: |
        Указан неверный идентификатор модели.

        Список доступных моделей и их идентификаторов — в разделе [Модели GigaChat](/ru/gigachat/models).
      content:
        application/json:
          schema:
            type: object
            properties:
              status:
                 type: integer
                 description: HTTP-код сообщения.
                 default: 404
              message:
                type: string
                description: Описание ошибки.
                default: No such model
    InternalError:
      description: Внутренняя ошибка сервера.
      content:
        application/json:
          schema:
            type: object
            properties:
              status:
                 type: integer
                 description: HTTP-код сообщения.
                 default: 500
              message:
                type: string
                description: Описание ошибки.
                default: Internal Server Error
    BadRequestFormat:
      description: |
        400 Bad request.

        Некорректный формат запроса.
    TooManyRequests:
      description: Слишком много запросов в единицу времени.
      content:
        application/json:
          schema:
            type: object
            properties:
              status:
                 type: integer
                 description: HTTP-код сообщения.
                 default: 429
              message:
                type: string
                description: Описание ошибки.
                default: Too many requests
    ValidationError:
      description: Ошибка валидации параметров запроса. Проверьте названия полей и значения параметров.
      content:
        application/json:
          schema:
            type: object
            properties:
              status:
                 type: integer
                 description: HTTP-код сообщения.
                 default: 422
              message:
                type: string
                description: Описание ошибки.
                example: "Invalid params: repetition_penalty must be in range (0, +inf)"
  securitySchemes:
    Базовая аутентификация:
      description: |
        Базовая (Basic) аутентификация с помощью ключа авторизации — строки, полученной в результате кодирования в base64 идентификатора (Client ID) и клиентского ключа (Client Secret) API.

        Ключ авторизации передается в заголовке `Authorization`, в запросе на [получение токена доступа](/ru/gigachat/api/reference/rest/post-token).

        <Admonition type="note">

        Как получить ключ авторизации и токен доступа Access token читайте в разделах [Быстрый старт для физических лиц](/ru/gigachat/individuals-quickstart) и [Быстрый старт для ИП и юридических лиц](/ru/gigachat/legal-quickstart).

        </Admonition>
      scheme: basic
      type: http
    Токен доступа:
      description: Аутентификация с помощью токена доступа Access token. Используется во всех запросах к GigaChat API, кроме запроса на [получение токена доступа](/ru/gigachat/api/reference/rest/post-token).
      type: http
      scheme: bearer
      bearerFormat: JWT
  
