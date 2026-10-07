# proyectojakatec

## Panel administrativo

El panel administrativo independiente se encuentra en `/admin/index.html`. El enlace está disponible desde la pantalla de inicio de sesión; al autenticarse, las cuentas autorizadas llegan directamente al panel y las demás continúan hacia la app.

El servidor protege las métricas, los reportes, las alertas y las acciones administrativas. Para autorizar cuentas, configura la variable de entorno `HEROESMX_ADMIN_EMAILS` con una lista de correos separados por comas, registra esas cuentas normalmente y reinicia el servidor:

```sh
HEROESMX_ADMIN_EMAILS="admin@ejemplo.mx,operaciones@ejemplo.mx" python3 server.py
```

Las cuentas no incluidas en esa lista conservan el rol de usuario. Nunca se asignan permisos administrativos desde el formulario de registro.

El panel permite consultar métricas y tendencias, revisar publicaciones y alertas en el mapa, filtrar y eliminar publicaciones reales, crear publicaciones oficiales y administrar misiones que aparecen en la sección Misiones de la comunidad. Los administradores pueden crear cuentas de personal, asignar roles de administrador o moderador, cambiar permisos y asociar fotos mediante una URL HTTPS. Los moderadores pueden revisar reportes en el mapa y actualizar su estado, pero no pueden cambiar permisos, crear cuentas de personal, publicar avisos ni administrar misiones. El mapa de calor muestra densidad relativa de reportes geolocalizados; al seleccionar un marcador, se puede consultar y actualizar el estado: pendiente, en revisión, atendido o descartado. Los reportes de demostración son solo de consulta. El mapa y los datos siguen siendo informativos: esta app no se conecta a C5 ni a servicios de emergencia.

## Publicaciones y reportes comunitarios

Desde Inicio se pueden crear publicaciones sociales o reportes comunitarios. Las publicaciones se muestran en el feed junto con noticias públicas; los reportes conservan su categoría, ubicación y estado, y alimentan el mapa y las métricas de reportes. Tanto publicaciones como reportes aceptan una foto JPG, PNG o WebP de hasta 5 MB, comentarios persistentes y compartir mediante el menú nativo del dispositivo o copiando un enlace. Cada persona puede cargar su foto de perfil desde Perfil; las imágenes cargadas se guardan localmente en `uploads/`, una carpeta excluida del control de versiones.