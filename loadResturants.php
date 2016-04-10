<?php
	require_once "ResturantDAO.php"; 
	$resturantDAO = new ResturantDAO;
	$resturantDAO->load_resturants();
?>