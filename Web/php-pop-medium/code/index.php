<?php
class FileWriter {
    public $file;
    public $payload;
    function write() {
        file_put_contents($this->file, $this->payload);
    }
}

class Trigger {
    public $obj;
    function __wakeup() {
        if ($this->obj && method_exists($this->obj, 'write')) {
            $this->obj->write();
        }
    }
}


?>
<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Challenge Medium — Interface</title>
<style>
:root{ --bg:#0f1724; --card:#0b1220; --muted:#94a3b8; --accent:#60a5fa; --glass: rgba(255,255,255,0.03);}
</style>
</head>
<body>
    <div>

<h1> Give me datas 2 !</h1>
<i>And try to get a shell :) </i>
<?php
if (isset($_GET['data'])) {
    $submitted = true;
    $data = $_GET['data'];
    $datas=unserialize(base64_decode($data));
    echo "<p>You submited :";
    print_r($datas);
    echo "</p>";
}
?>
<hr/>
<h2>Code</h2>
<pre>
<?php 
 highlight_file('./index.php')
?>
</pre>

</html>%    