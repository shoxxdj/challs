<?php
class Writer {
    public $path;
    public $content;
    
    
    function __construct($path = null, $content = null) {
        if ($path !== null) $this->path = $path;
        if ($content !== null) $this->content = $content;
    }
    
    
    function __destruct() {
        if (!empty($this->path) && isset($this->content)) {
            @file_put_contents($this->path, $this->content);
        }
    }
}

class Container {
    public $w;
}

$resultMessage = null;
$submitted = false;

?>
<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Challenge Easy — Interface</title>
<style>
:root{ --bg:#0f1724; --card:#0b1220; --muted:#94a3b8; --accent:#60a5fa; --glass: rgba(255,255,255,0.03);}
</style>
</head>
<body>
    <div>

<h1> Give me datas !</h1>
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

</html>